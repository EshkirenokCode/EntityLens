# Evaluation

See `reports/evaluation.json` and `reports/split-manifest.json`. This is a silver geographic development experiment, not an independently reviewed benchmark. Repeating the command is reproducibility work; tuning from holdout errors requires reclassifying this holdout as development and collecting a new sealed test.

Baseline: F1 0.99856, 347 true positives, 1 false positive, 0 false negatives, 3,348 true negatives. Both trained variants: 347 true positives, 0 false positives, 0 false negatives, 3,349 true negatives. The classifier learns the weak-label construction; perfect scores do not establish real accuracy. The added SVD feature has no measured benefit. Keep the simpler lexical/spatial model.

Auto-link coverage: 0. Review share: 1. Independent candidate recall, end-to-end recall, latent-entity disjointness, B-cubed quality and production calibration are unmeasured. No confidence interval on silver-rule agreement would repair the lack of independent truth.

Next evaluation: independently review `reports/label-queue.json`, adjudicate conservative entity groups before splitting, search for missed matches outside retrieval, select risk/coverage thresholds on validation and evaluate a newly sealed gold test once. Challenge strata and random-population results must remain separate.
