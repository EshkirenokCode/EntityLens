import sys, pathlib, json, hashlib, math

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from entitylens.features import candidates


def load(source):
    m = json.loads((ROOT / f"data/manifests/{source}.json").read_text())
    p = ROOT / m["path"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == m["sha256"]
    return json.loads(p.read_text())


def coord(v):
    try:
        f = float(v)
        return f if math.isfinite(f) and f else None
    except (TypeError, ValueError):
        return None


records = []
seen = set()
for r in load("nyc"):
    if r["camis"] in seen:
        continue
    seen.add(r["camis"])
    records.append(
        dict(
            id="nyc:" + r["camis"],
            source="nyc",
            name=r.get("dba", ""),
            address=(r.get("building", "") + " " + r.get("street", "")).strip(),
            lat=coord(r.get("latitude")),
            lon=coord(r.get("longitude")),
            phone=r.get("phone", ""),
            raw=r,
        )
    )
for row in load("overture")["features"]:
    r = row["properties"]
    cat = (
        str(r.get("basic_category", ""))
        + " "
        + str(r.get("taxonomy", ""))
        + " "
        + str(r.get("categories", ""))
    )
    if "food_and_drink" not in ((r.get("taxonomy") or {}).get("hierarchy") or []):
        continue
    addresses = r.get("addresses") or [{}]
    phones = r.get("phones") or [""]
    xy = row["geometry"]["coordinates"]
    records.append(
        dict(
            id="overture:" + row["id"],
            source="overture",
            name=(r.get("names") or {}).get("primary", ""),
            address=(addresses[0].get("freeform") or ""),
            lat=coord(xy[1]),
            lon=coord(xy[0]),
            phone="".join(c for c in phones[0] if c.isdigit())[-10:],
            raw=r,
        )
    )
for r in records:
    r["version"] = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()[
        :16
    ]
out = ROOT / "data/processed"
out.mkdir(exist_ok=True)
(out / "records.json").write_text(json.dumps(records))
left = [r for r in records if r["source"] == "nyc"]
right = [r for r in records if r["source"] == "overture"]
pairs = [
    dict(
        id=hashlib.sha256("|".join(sorted([a["id"], b["id"]])).encode()).hexdigest()[
            :20
        ],
        left=a["id"],
        right=b["id"],
        versions=[a["version"], b["version"]],
        features=f,
        baseline=s,
        score=s,
        status="REVIEW",
    )
    for a, b, f, s in candidates(left, right)
]
(out / "pairs.json").write_text(json.dumps(pairs))
report = dict(
    records=len(records),
    sources={s: sum(r["source"] == s for r in records) for s in ["nyc", "overture"]},
    candidates=len(pairs),
    reduction_ratio=1 - len(pairs) / max(1, len(left) * len(right)),
    missingness={
        s: {
            k: sum(not r.get(k) for r in records if r["source"] == s)
            / max(1, sum(r["source"] == s for r in records))
            for k in ["name", "address", "phone", "lat"]
        }
        for s in ["nyc", "overture"]
    },
    label_status="No independently reviewed gold",
    candidate_recall=None,
)
(ROOT / "reports/data-quality.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
