import os, json, sqlite3, uuid, time, hashlib
from pathlib import Path
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
DB = os.environ.get("CONCORD_DB", str(ROOT / "concord-v1.db"))


@contextmanager
def connect():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.create_function(
        "casefold", 1, lambda value: str(value or "").casefold(), deterministic=True
    )
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA journal_mode=WAL")
    try:
        with c:
            yield c
    finally:
        c.close()


def init():
    with connect() as c:
        c.executescript("""
 CREATE TABLE IF NOT EXISTS record_versions(record_id TEXT,version TEXT,payload TEXT,observed REAL,PRIMARY KEY(record_id,version));
 CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS pairs(id TEXT PRIMARY KEY,payload TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1);
 CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,pair_id TEXT,kind TEXT,rationale TEXT,created REAL,undone INTEGER DEFAULT 0,idempotency TEXT UNIQUE);
 CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT,payload TEXT,created REAL);
 CREATE TABLE IF NOT EXISTS decision_records(decision_id TEXT,record_id TEXT,payload TEXT NOT NULL,PRIMARY KEY(decision_id,record_id));
 CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,status TEXT,attempts INTEGER DEFAULT 0,lease REAL,error TEXT,created REAL);
 """)


def bootstrap():
    init()
    with connect() as c:
        for path, table in [("records", "records"), ("pairs", "pairs")]:
            p = ROOT / f"data/processed/{path}.json"
            if p.exists():
                for row in json.loads(p.read_text()):
                    c.execute(
                        f"INSERT OR IGNORE INTO {table}(id,payload) VALUES(?,?)",
                        (row["id"], json.dumps(row)),
                    )

        for d in c.execute(
            "SELECT d.id,p.payload FROM decisions d JOIN pairs p ON p.id=d.pair_id WHERE d.undone=0"
        ):
            pair = json.loads(d["payload"])
            for rid, version in zip([pair["left"], pair["right"]], pair["versions"]):
                current = c.execute(
                    "SELECT payload FROM records WHERE id=?", (rid,)
                ).fetchone()
                historical = c.execute(
                    "SELECT payload FROM record_versions WHERE record_id=? AND version=?",
                    (rid, version),
                ).fetchone()
                payload = (
                    historical["payload"]
                    if historical
                    else current["payload"]
                    if current and json.loads(current["payload"])["version"] == version
                    else None
                )
                if payload:
                    c.execute(
                        "INSERT OR IGNORE INTO decision_records VALUES(?,?,?)",
                        (d["id"], rid, payload),
                    )


def rows(c, table):
    return [json.loads(r["payload"]) for r in c.execute(f"SELECT payload FROM {table}")]


def components(c, excluding=None):
    records = {r["id"]: r for r in rows(c, "records")}
    parent = {k: k for k in records}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    pairs = {
        r["id"]: json.loads(r["payload"])
        for r in c.execute(
            "SELECT DISTINCT p.id,p.payload FROM pairs p JOIN decisions d ON d.pair_id=p.id WHERE d.undone=0"
        )
    }
    ds = list(c.execute("SELECT * FROM decisions WHERE undone=0 ORDER BY created,id"))
    cannot = []
    for d in ds:
        if d["id"] == excluding:
            continue
        p = pairs[d["pair_id"]]
        if d["kind"] == "DIFFERENT":
            cannot.append((p["left"], p["right"]))
    for d in ds:
        if d["id"] == excluding or d["kind"] != "SAME":
            continue
        p = pairs[d["pair_id"]]
        a, b = find(p["left"]), find(p["right"])
        parent[b] = a
    for a, b in cannot:
        if find(a) == find(b):
            raise ValueError("Cannot-link conflict across the proposed group")
    groups = {}
    for k in records:
        groups.setdefault(find(k), []).append(k)
    return list(groups.values()), records


def decide(pair_id, kind, rationale, revision, key, context_version=None):
    if kind not in ("SAME", "DIFFERENT", "UNCERTAIN"):
        raise ValueError("Invalid decision")
    if not rationale.strip():
        raise ValueError("Evidence rationale is required")
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        old = c.execute(
            "SELECT * FROM decisions WHERE idempotency=?", (key,)
        ).fetchone()
        if old:
            if (
                old["pair_id"] != pair_id
                or old["kind"] != kind
                or old["rationale"] != rationale
            ):
                raise ValueError("Idempotency key reused with different payload")
            return dict(old)
        row = c.execute("SELECT * FROM pairs WHERE id=?", (pair_id,)).fetchone()
        if not row:
            raise KeyError(pair_id)
        p = json.loads(row["payload"])
        if row["revision"] != revision:
            raise ValueError("Stale proposal: refresh before confirming")
        rs = {r["id"]: r for r in rows(c, "records")}
        if [rs[k]["version"] for k in [p["left"], p["right"]]] != p["versions"]:
            raise ValueError("Source changed: proposal requires reevaluation")
        if c.execute(
            "SELECT 1 FROM decisions WHERE pair_id=? AND undone=0", (pair_id,)
        ).fetchone():
            raise ValueError("Undo the existing decision first")
        if (
            context_version is not None
            and review_context(c, pair_id)["context_version"] != context_version
        ):
            raise ValueError("Group changed since preview: refresh before confirming")
        if kind == "SAME":
            blockers = merge_blockers(c, pair_id)
            if blockers:
                raise ValueError(blockers[0]["message"])
        ident = str(uuid.uuid4())
        c.execute(
            "INSERT INTO decisions(id,pair_id,kind,rationale,created,idempotency) VALUES(?,?,?,?,?,?)",
            (ident, pair_id, kind, rationale, time.time(), key),
        )
        for rid in [p["left"], p["right"]]:
            c.execute(
                "INSERT INTO decision_records VALUES(?,?,?)",
                (ident, rid, json.dumps(rs[rid])),
            )
        groups, _ = components(c)
        p["status"] = kind
        c.execute(
            "UPDATE pairs SET payload=?,revision=revision+1 WHERE id=?",
            (json.dumps(p), pair_id),
        )
        c.execute(
            "INSERT INTO events(kind,payload,created) VALUES(?,?,?)",
            (
                "review",
                json.dumps(
                    dict(
                        id=ident,
                        pair=pair_id,
                        kind=kind,
                        author="local analyst",
                        rationale=rationale,
                        record_versions=p["versions"],
                        model=p.get("model", "rule baseline"),
                        policy="review-only",
                        groups=[g for g in groups if p["left"] in g or p["right"] in g],
                    )
                ),
                time.time(),
            ),
        )
        return dict(id=ident, kind=kind)


def undo(ident):
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        d = c.execute("SELECT * FROM decisions WHERE id=?", (ident,)).fetchone()
        if not d:
            raise KeyError(ident)
        if d["undone"]:
            return
        c.execute("UPDATE decisions SET undone=1 WHERE id=?", (ident,))
        components(c)
        row = c.execute(
            "SELECT payload FROM pairs WHERE id=?", (d["pair_id"],)
        ).fetchone()
        p = json.loads(row[0])
        p["status"] = "REVIEW"
        c.execute(
            "UPDATE pairs SET payload=?,revision=revision+1 WHERE id=?",
            (json.dumps(p), d["pair_id"]),
        )
        c.execute(
            "INSERT INTO events(kind,payload,created) VALUES(?,?,?)",
            ("undo", json.dumps(dict(decision=ident)), time.time()),
        )


def review_context(c, pair_id):
    row = c.execute("SELECT payload FROM pairs WHERE id=?", (pair_id,)).fetchone()
    if not row:
        raise KeyError(pair_id)
    pair = json.loads(row["payload"])
    groups, rs = components(c)
    affected = sorted(
        {k for g in groups if pair["left"] in g or pair["right"] in g for k in g}
    )
    touched = []
    for d in c.execute(
        "SELECT d.id,d.kind,p.payload FROM decisions d JOIN pairs p ON p.id=d.pair_id WHERE d.undone=0 ORDER BY d.id"
    ):
        p = json.loads(d["payload"])
        if p["left"] in affected or p["right"] in affected:
            touched.append((d["id"], d["kind"]))
    version = hashlib.sha256(
        json.dumps(
            [[(k, rs[k]["version"]) for k in affected], touched], sort_keys=True
        ).encode()
    ).hexdigest()
    return dict(
        pair_id=pair_id,
        context_version=version,
        members=[
            dict(
                id=k,
                name=rs[k]["name"],
                address=rs[k]["address"],
                version=rs[k]["version"],
            )
            for k in affected
        ],
        record_versions=pair["versions"],
        policy="Full group checked for cannot-link and location conflicts on confirmation",
        merge_blockers=merge_blockers(c, pair_id),
    )


def reviewed_members(c, group, current):
    if len(group) < 2:
        return {k: current[k] for k in group}, []
    historical = {}
    changed = set()
    for d in c.execute(
        "SELECT d.id,p.payload FROM decisions d JOIN pairs p ON p.id=d.pair_id WHERE d.undone=0 AND d.kind='SAME' ORDER BY d.created,d.id"
    ):
        p = json.loads(d["payload"])
        if p["left"] not in group:
            continue
        for rid, version in zip([p["left"], p["right"]], p["versions"]):
            row = c.execute(
                "SELECT payload FROM decision_records WHERE decision_id=? AND record_id=?",
                (d["id"], rid),
            ).fetchone()
            record = json.loads(row["payload"]) if row else None
            if record is None or record["version"] != current[rid]["version"]:
                changed.add(rid)
            if record is not None:
                if (
                    rid in historical
                    and historical[rid]["version"] != record["version"]
                ):
                    changed.add(rid)
                historical.setdefault(rid, record)
    for rid in group:
        if rid not in historical:
            historical[rid] = dict(
                id=rid,
                source=current[rid]["source"],
                name="Reviewed record unavailable",
                address="",
                phone="",
                lat=None,
                lon=None,
                version="unknown",
            )
            changed.add(rid)
    return historical, sorted(changed)


def merge_blockers(c, pair_id):
    from concord.identity import location_blockers

    row = c.execute("SELECT payload FROM pairs WHERE id=?", (pair_id,)).fetchone()
    if not row:
        raise KeyError(pair_id)
    pair = json.loads(row["payload"])
    groups, rs = components(c)
    affected = sorted(
        {
            k
            for group in groups
            if pair["left"] in group or pair["right"] in group
            for k in group
        }
    )
    blockers = []
    if pair["versions"] != [rs[pair["left"]]["version"], rs[pair["right"]]["version"]]:
        blockers.append(
            dict(
                code="source_changed",
                message="Source changed: proposal requires reevaluation",
                records=[pair["left"], pair["right"]],
            )
        )
    for group in groups:
        if pair["left"] in group or pair["right"] in group:
            _, changed = reviewed_members(c, group, rs)
            if changed:
                blockers.append(
                    dict(
                        code="group_changed",
                        message="Group contains changed source records: undo and reevaluate the affected links first",
                        records=changed,
                    )
                )
    for row in c.execute(
        "SELECT p.payload FROM pairs p JOIN decisions d ON p.id=d.pair_id WHERE d.undone=0 AND d.kind='DIFFERENT'"
    ):
        p = json.loads(row["payload"])
        if p["left"] in affected and p["right"] in affected:
            blockers.append(
                dict(
                    code="cannot_link",
                    message="Cannot-link conflict across the proposed group",
                    records=[p["left"], p["right"]],
                )
            )
    if len(affected) > 12:
        blockers.append(
            dict(
                code="group_size",
                message="Group exceeds review safety limit",
                records=affected,
            )
        )
    return blockers + location_blockers([rs[k] for k in affected])
