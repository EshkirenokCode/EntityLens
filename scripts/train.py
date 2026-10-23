"""CPU experiment on silver labels; never authorizes automatic linking."""

import sys, pathlib, json, hashlib, time, platform, subprocess, pickle, os

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    confusion_matrix,
    brier_score_loss,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from concord.features import SCHEMA, NAMES

SEED = 42
start = time.time()
records = json.loads((ROOT / "data/processed/records.json").read_text())
rs = {r["id"]: r for r in records}
pairs = json.loads((ROOT / "data/processed/pairs.json").read_text())


# Conservative leakage components include ALL retrieved edges, not predicted matches.
# Dense spatial neighborhoods may form giant components; geographic holdout is used instead.
# Only pairs fully within a geographic partition are admitted; no record can cross splits.
def split(r):
    lon = r.get("lon")
    return (
        "train"
        if lon is not None and lon < -73.999
        else "validation"
        if lon is not None and lon < -73.993
        else "test"
    )


labels = []
for p in pairs:
    a, b = rs[p["left"]], rs[p["right"]]
    f = p["features"]
    sa, sb = split(a), split(b)
    if sa != sb:
        continue
    # Weak supervision uses names, addresses and proximity, with ambiguity excluded.
    if f[0] >= 0.86 and f[2] >= 0.72 and f[4] >= 0.37 and f[3]:
        label = 1
    elif f[0] < 0.42 and (f[2] < 0.55 or f[4] < 0.15):
        label = 0
    else:
        continue
    labels.append(
        dict(
            pair=p["id"],
            left=a["id"],
            right=b["id"],
            label=label,
            split=sa,
            provenance="silver",
            method="name-address-spatial-v1",
            record_versions=p["versions"],
        )
    )
by = {
    s: [r for r in labels if r["split"] == s] for s in ["train", "validation", "test"]
}
lookup = {p["id"]: p for p in pairs}
for s, rows in by.items():
    if len({r["label"] for r in rows}) < 2:
        raise RuntimeError(
            f"Insufficient class support in {s}; enlarge data before training"
        )
sets = {s: {k for r in rows for k in [r["left"], r["right"]]} for s, rows in by.items()}
assert not any(
    sets[a] & sets[b]
    for a, b in [("train", "test"), ("train", "validation"), ("validation", "test")]
)
# Fit lexical embeddings exclusively on training records. This is an SVD ablation,
# not a pretrained neural encoder or a fine-tuned neural model.
ids = sorted(sets["train"])
vectorizer = TfidfVectorizer(
    analyzer="char_wb", ngram_range=(2, 4), min_df=2, max_features=8000
)
text = lambda r: (r["name"] or "") + " " + (r["address"] or "")
z = vectorizer.fit_transform([text(rs[k]) for k in ids])
svd = TruncatedSVD(n_components=min(32, z.shape[1] - 1), random_state=SEED)
svd.fit(z)
allids = sorted(rs)
emb = svd.transform(vectorizer.transform([text(rs[k]) for k in allids]))
emb /= np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-9)
embedding = {k: v for k, v in zip(allids, emb)}


def matrix(rows, mode):
    out = []
    for r in rows:
        p = lookup[r["pair"]]
        f = p["features"]
        # Contact features excluded: ablation documents their limited availability.
        base = f[:5] + f[6:]
        if mode == "lexical + SVD":
            base = base + [float(embedding[p["left"]] @ embedding[p["right"]])]
        out.append(base)
    return np.array(out)


def metrics(y, score, threshold):
    pred = score >= threshold
    return dict(
        n=len(y),
        positive=int(sum(y)),
        precision=float(precision_score(y, pred, zero_division=0)),
        recall=float(recall_score(y, pred, zero_division=0)),
        f1=float(f1_score(y, pred, zero_division=0)),
        pr_auc=float(average_precision_score(y, score)),
        brier=float(brier_score_loss(y, score)),
        confusion=confusion_matrix(y, pred, labels=[0, 1]).tolist(),
        threshold=threshold,
        auto_link_coverage=0,
        review_share=1,
    )


y = {s: np.array([r["label"] for r in rows]) for s, rows in by.items()}
results = {}
trained = {}
val_results = {}
for mode in ["lexical / spatial", "lexical + SVD"]:
    model = HistGradientBoostingClassifier(
        max_iter=100, max_leaf_nodes=15, l2_regularization=2, random_state=SEED
    )
    model.fit(matrix(by["train"], mode), y["train"])
    vp = model.predict_proba(matrix(by["validation"], mode))[:, 1]
    thresholds = [0.3, 0.5, 0.7, 0.9]
    threshold = max(thresholds, key=lambda t: f1_score(y["validation"], vp >= t))
    val_results[mode] = metrics(y["validation"], vp, threshold)
    trained[mode] = (model, threshold)
# Lock selection from validation before accessing test predictions.
best = max(val_results, key=lambda k: val_results[k]["f1"])
artifact = ROOT / "artifacts"
artifact.mkdir(exist_ok=True)
for mode, (model, threshold) in trained.items():
    results[mode] = metrics(
        y["test"], model.predict_proba(matrix(by["test"], mode))[:, 1], threshold
    )
for s in ["validation", "test"]:
    scores = np.array([lookup[r["pair"]]["baseline"] for r in by[s]])
    if s == "validation":
        bt = max([0.3, 0.5, 0.7, 0.9], key=lambda t: f1_score(y[s], scores >= t))
    else:
        results["rule baseline"] = metrics(y[s], scores, bt)
manifest = dict(
    seed=SEED,
    method="fixed longitude geographic partition, discard crossing pairs",
    boundaries=[-73.999, -73.993],
    labels=labels,
    counts={
        s: dict(pairs=len(r), positive=sum(x["label"] for x in r))
        for s, r in by.items()
    },
    limitations=[
        "Geographic partition guarantees record disjointness, not independently verified entity disjointness.",
        "Cross-boundary duplicates and chains may remain; independent adjudication required.",
    ],
)
mhash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
(ROOT / "reports/split-manifest.json").write_text(json.dumps(manifest, indent=2))
model, threshold = trained[best]
bundle = dict(
    schema=SCHEMA,
    feature_names=NAMES,
    model=model,
    mode=best,
    vectorizer=vectorizer,
    svd=svd,
    threshold=threshold,
    policy="review-only",
    manifest_hash=mhash,
)
with open(artifact / "model.pkl", "wb") as f:
    pickle.dump(bundle, f)
report = dict(
    status="Silver geographic holdout",
    label_provenance="Heuristic silver labels; no independent human gold",
    gold_available=False,
    models=results,
    validation=val_results,
    selected=best,
    selection="validation F1 only; test read after locking configuration",
    manifest_hash=mhash,
    split_counts=manifest["counts"],
    training_seconds=time.time() - start,
    hardware=dict(
        platform=platform.platform(), cpu=platform.processor(), cores=os.cpu_count()
    ),
    source_hashes={
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            ROOT / "scripts/train.py",
            ROOT / "concord/features.py",
            ROOT / "concord/inference.py",
        ]
    },
    data_manifests={
        p.stem: json.loads(p.read_text())["sha256"]
        for p in (ROOT / "data/manifests").glob("*.json")
    },
    code_revision=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip(),
    policy="review-only",
    candidate_recall=None,
    cluster_metrics=None,
    neural_finetuning="Deferred: no independently verified real labels",
    limitations=manifest["limitations"]
    + [
        "Label features overlap model features: metrics are heuristic agreement, not independent accuracy.",
        "SVD is a train-only lexical embedding, not a pretrained multilingual neural encoder.",
    ],
)
(ROOT / "reports/evaluation.json").write_text(json.dumps(report, indent=2))
(artifact / "manifest.json").write_text(
    json.dumps({k: v for k, v in report.items() if k != "models"}, indent=2)
)
print(json.dumps(report, indent=2))
# Score every candidate using exactly the trained feature serialization.
from concord.inference import score_pairs

score_pairs(pairs, rs, bundle)
(ROOT / "data/processed/pairs.json").write_text(json.dumps(pairs))
# Persist keyed prediction/error samples without redistributing source contact data.
test_scores = model.predict_proba(matrix(by["test"], best))[:, 1]
output = [
    dict(
        pair=r["pair"],
        label=r["label"],
        score=float(s),
        prediction=int(s >= threshold),
        provenance="silver",
        split="test",
    )
    for r, s in zip(by["test"], test_scores)
]
(ROOT / "reports/predictions.jsonl").write_text(
    "".join(json.dumps(row) + "\n" for row in output)
)
(ROOT / "reports/errors.json").write_text(
    json.dumps([row for row in output if row["label"] != row["prediction"]], indent=2)
)
