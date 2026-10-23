import os, json, sqlite3, uuid, time
from pathlib import Path
from contextlib import contextmanager

DB = os.environ.get("CONCORD_DB", "concord.db")


@contextmanager
def connect():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
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
 CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,status TEXT,attempts INTEGER DEFAULT 0,lease REAL,error TEXT,created REAL);
 """)


def bootstrap():
    init()
    with connect() as c:
        for path, table in [("records", "records"), ("pairs", "pairs")]:
            p = Path(f"data/processed/{path}.json")
            if p.exists():
                for row in json.loads(p.read_text()):
                    c.execute(
                        f"INSERT OR IGNORE INTO {table}(id,payload) VALUES(?,?)",
                        (row["id"], json.dumps(row)),
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


def decide(pair_id, kind, rationale, revision, key):
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
        ident = str(uuid.uuid4())
        c.execute(
            "INSERT INTO decisions(id,pair_id,kind,rationale,created,idempotency) VALUES(?,?,?,?,?,?)",
            (ident, pair_id, kind, rationale, time.time(), key),
        )
        groups, _ = components(c)
        if kind == "SAME":
            from concord.features import distance

            for group in groups:
                if p["left"] not in group:
                    continue
                for i, a in enumerate(group):
                    for b in group[i + 1 :]:
                        d = distance(rs[a], rs[b])
                        import re

                        ha = re.match(r"^\d+", rs[a]["address"])
                        hb = re.match(r"^\d+", rs[b]["address"])
                        if ha and hb and ha[0] != hb[0]:
                            raise ValueError(
                                "Conflicting street numbers: resolve source evidence before merging branches"
                            )
                        if d is not None and d > 300:
                            raise ValueError(
                                "Conflicting coordinates exceed the location safety limit"
                            )
        if any(len(g) > 12 for g in groups):
            raise ValueError("Group exceeds review safety limit")
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
