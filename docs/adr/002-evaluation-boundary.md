# ADR 002: review-only policy on silver evidence

Accepted 2026-10-24. Train the first classifier on transparent automatic silver rules and isolate geographic record partitions. Preserve labels, source versions and manifest hashes. Do not call these labels independently reviewed, or claim perfect holdout scores establish place accuracy. A train-only SVD ablation is useful as a low-cost representation experiment; a multilingual encoder and fine-tuning require a better evaluation set before interpreting benefit.

All live proposals require review regardless of model score. Validation chooses thresholds and model, while test is read after configuration locks. Known limitations include latent entities crossing geographic partitions, excluded ambiguous pairs and label/feature dependence. The next independent adjudicated benchmark must establish entity grouping before split assignment and include missed retrieval candidates.
