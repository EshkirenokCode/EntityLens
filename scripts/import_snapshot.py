"""Admin-only prepared snapshot update. Preserve every immutable record version."""

import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from concord import store

store.init()
records = json.loads((ROOT / "data/processed/records.json").read_text())
changed = 0
with store.connect() as c:
    c.execute("BEGIN IMMEDIATE")
    for r in records:
        old = c.execute("SELECT payload FROM records WHERE id=?", (r["id"],)).fetchone()
        if old:
            previous = json.loads(old[0])
            c.execute(
                "INSERT OR IGNORE INTO record_versions VALUES(?,?,?,?)",
                (previous["id"], previous["version"], old[0], time.time()),
            )
            if previous["version"] != r["version"]:
                changed += 1
                c.execute(
                    "INSERT INTO events(kind,payload,created) VALUES(?,?,?)",
                    (
                        "source_changed",
                        json.dumps(
                            dict(
                                record=r["id"],
                                before=previous["version"],
                                after=r["version"],
                            )
                        ),
                        time.time(),
                    ),
                )
        c.execute(
            "INSERT OR IGNORE INTO record_versions VALUES(?,?,?,?)",
            (r["id"], r["version"], json.dumps(r), time.time()),
        )
        c.execute(
            "INSERT INTO records(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (r["id"], json.dumps(r)),
        )
print(
    f"Imported {len(records)} records; {changed} changed. Old proposals stay stale until matching reruns. Missing records are not closed."
)
