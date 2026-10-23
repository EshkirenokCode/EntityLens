"""Small local model registry. Activation always retains review-only policy."""

import argparse, hashlib, json, pathlib, shutil, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts"
REG = BASE / "registry"
REG.mkdir(parents=True, exist_ok=True)
p = argparse.ArgumentParser()
p.add_argument(
    "action", choices=["register", "evaluate", "activate", "rollback", "list"]
)
p.add_argument("--version")
args = p.parse_args()
index = REG / "index.json"
state = (
    json.loads(index.read_text())
    if index.exists()
    else dict(models={}, active=None, previous=None)
)
if args.action == "register":
    digest = hashlib.sha256((BASE / "model.pkl").read_bytes()).hexdigest()
    v = hashlib.sha256(
        (BASE / "model.pkl").read_bytes() + (BASE / "manifest.json").read_bytes()
    ).hexdigest()[:16]
    folder = REG / v
    folder.mkdir(exist_ok=True)
    if v not in state["models"]:
        shutil.copy2(BASE / "model.pkl", folder / "model.pkl")
        shutil.copy2(BASE / "manifest.json", folder / "manifest.json")
    state["models"].setdefault(
        v,
        dict(
            state="candidate",
            sha256=digest,
            registered=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            policy="review-only",
        ),
    )
    print(v)
elif args.action == "evaluate":
    v = args.version
    assert v in state["models"]
    report = json.loads((ROOT / "reports/evaluation.json").read_text())
    model = json.loads((REG / v / "manifest.json").read_text())
    assert report["manifest_hash"] == model["manifest_hash"]
    state["models"][v]["state"] = "evaluated"
elif args.action in ("activate", "rollback"):
    v = args.version if args.action == "activate" else state["previous"]
    assert v in state["models"]
    assert state["models"][v]["state"] in ["evaluated", "active", "retired"]
    payload = (REG / v / "model.pkl").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == state["models"][v]["sha256"]
    old = state["active"]
    state["previous"] = old
    state["active"] = v
    if old:
        state["models"][old]["state"] = "retired"
    state["models"][v]["state"] = "active"
    temporary = BASE / "model.next"
    temporary.write_bytes(payload)
    temporary.replace(BASE / "model.pkl")
    shutil.copy2(REG / v / "manifest.json", BASE / "manifest.json")
index.write_text(json.dumps(state, indent=2))
print(json.dumps(state, indent=2))
