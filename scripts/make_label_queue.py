"""Reproducible review sample; does not assign ground truth."""

import json, pathlib, random, hashlib

root = pathlib.Path(__file__).resolve().parents[1]
ps = json.loads((root / "data/processed/pairs.json").read_text())
rs = {
    r["id"]: r for r in json.loads((root / "data/processed/records.json").read_text())
}
rng = random.Random(42)
strata = {
    "random": rng.sample(ps, min(40, len(ps))),
    "similar_names": sorted(
        ps, key=lambda p: (-p["features"][0], p["features"][3], p["features"][4])
    )[:20],
    "ambiguous": sorted(ps, key=lambda p: abs(p["baseline"] - 0.65))[:20],
}
queue = []
for stratum, items in strata.items():
    for p in items:
        queue.append(
            dict(
                pair=p["id"],
                stratum=stratum,
                record_ids=[p["left"], p["right"]],
                record_versions=p["versions"],
                source_refs=[
                    {
                        "source": rs[k]["source"],
                        "source_id": k,
                        "version": rs[k]["version"],
                    }
                    for k in [p["left"], p["right"]]
                ],
                label=None,
                rationale=None,
                evidence_urls=[],
                reviewer=None,
                provenance="unlabeled",
                independently_verified=False,
            )
        )
(root / "reports/label-queue.json").write_text(json.dumps(queue, indent=2))
print(f"Prepared {len(queue)} unlabeled samples; strata are not population prevalence.")
