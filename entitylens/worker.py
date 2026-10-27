"""Single durable local worker with bounded retry and expiring lease."""

import time, json, uuid, pickle
from pathlib import Path
from entitylens import store
from entitylens.features import candidates
from entitylens.inference import score_pairs

store.init()


def tick():
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        now = time.time()
        c.execute(
            "UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'queued' END,lease=NULL WHERE status='running' AND lease<?",
            (now,),
        )
        r = c.execute(
            "SELECT * FROM jobs WHERE status='queued' AND attempts<3 ORDER BY created LIMIT 1"
        ).fetchone()
        if not r:
            return False
        ident = r["id"]
        token = now + 300
        c.execute(
            "UPDATE jobs SET status='running',lease=?,attempts=attempts+1 WHERE id=?",
            (token, ident),
        )
        records = store.rows(c, "records")
    try:
        import hashlib

        left = [r for r in records if r["source"] == "nyc"]
        right = [r for r in records if r["source"] == "overture"]
        ps = []
        for a, b, f, s in candidates(left, right):
            ps.append(
                dict(
                    id=hashlib.sha256(
                        "|".join(sorted([a["id"], b["id"]])).encode()
                    ).hexdigest()[:20],
                    left=a["id"],
                    right=b["id"],
                    versions=[a["version"], b["version"]],
                    features=f,
                    baseline=s,
                    score=s,
                    status="REVIEW",
                )
            )
        if (store.ROOT / "artifacts/model.pkl").exists():
            with open(store.ROOT / "artifacts/model.pkl", "rb") as fh:
                bundle = pickle.load(fh)
            score_pairs(ps, {r["id"]: r for r in records}, bundle)
        with store.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            job = c.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            if (
                job["status"] != "running"
                or job["lease"] != token
                or time.time() > token
            ):
                raise ValueError("Job lease no longer valid")
            current = {r["id"]: r["version"] for r in store.rows(c, "records")}
            if current != {r["id"]: r["version"] for r in records}:
                raise ValueError(
                    "Source changed during matching; retry with current snapshot"
                )
            current_ids = {p["id"] for p in ps}
            for row in c.execute(
                "SELECT id,payload FROM pairs WHERE json_extract(payload,'$.status')='REVIEW'"
            ).fetchall():
                if row["id"] not in current_ids:
                    retired = json.loads(row["payload"])
                    retired["status"] = "RETIRED"
                    c.execute(
                        "UPDATE pairs SET payload=?,revision=revision+1 WHERE id=?",
                        (json.dumps(retired), row["id"]),
                    )
            for p in ps:
                old = c.execute(
                    "SELECT payload FROM pairs WHERE id=?", (p["id"],)
                ).fetchone()
                if old:
                    before = json.loads(old[0])
                    if before["status"] not in ("REVIEW", "RETIRED"):
                        continue
                    c.execute(
                        "UPDATE pairs SET payload=?,revision=revision+1 WHERE id=?",
                        (json.dumps(p), p["id"]),
                    )
                else:
                    c.execute(
                        "INSERT INTO pairs(id,payload) VALUES(?,?)",
                        (p["id"], json.dumps(p)),
                    )
            c.execute(
                "UPDATE jobs SET status='completed',lease=NULL,error=NULL WHERE id=?",
                (ident,),
            )
    except Exception as e:
        with store.connect() as c:
            c.execute(
                "UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'queued' END,error=?,lease=NULL WHERE id=? AND lease=?",
                (str(e)[:500], ident, token),
            )
    return True


if __name__ == "__main__":
    try:
        while True:
            if not tick():
                time.sleep(2)
    except KeyboardInterrupt:
        pass
