# Model card

CPU-trained scikit-learn HistGradientBoostingClassifier, seed 42, 100 iterations, 15 maximum leaf nodes, L2 regularization 2. Shared lexical, address, house-number, geographic proximity and missingness features. Phone equality is excluded from the learned classifier. Rule baseline remains separately measurable.

Training uses 4,910 silver pairs (357 positive), validation 2,522 (290 positive), geographic test 3,696 (347 positive). Threshold selected from validation F1. Source IDs, label provenance and canonical IDs do not enter features. Split details and record versions are in the machine-readable manifest.

The optional train-only character TF-IDF → 32-dimensional truncated SVD cosine feature produces no improvement on silver labels. This is a lexical representation experiment, not a pretrained multilingual encoder or neural fine-tuning. Neural fine-tuning is deferred until sufficient independently verified labels exist.

Both trained variants perfectly reproduce silver labels on this holdout. This reflects overlapping label rules and features, not independently established matching accuracy. Baseline F1 is 0.99856 with one silver false positive. No calibration or automatic linking is authorized by these results. Scores are similarity scores, not independently calibrated probabilities.

Artifacts are generated locally by `scripts/train.py`; never load visitor-provided pickle files. Feature schema mismatch prevents scoring. Review-only is always active. Real branch, missing-counterpart, renaming and transitive-conflict judgments still require analyst evidence.
