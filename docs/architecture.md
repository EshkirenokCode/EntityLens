# Concord architecture

Concord resolves physical food establishments across independent catalogs. A location is the identity boundary; brands and legal entities are out of scope.

## Product and delivery

The analyst imports immutable snapshots, inspects candidate pairs, records evidence and decisions, and exports canonical entities with field provenance. English workbench screens: Sources & Runs, Review, Entities, Evaluation.

1. Feasibility: verify NYC DOHMH and Overture access, source terms and schema; bounded Lower Manhattan extract.
2. Vertical: adapters, normalization, candidate retrieval, rule baseline, durable review and canonical lineage.
3. Learning: explicit label provenance, component-disjoint manifests, trained tabular model and baseline comparison.
4. Safety: cannot-link constraints, stale checks, history, undo and source updates.
5. Experiments and packaging: ablations, registry, monitoring, tests, browser verification, reproducible reports.

## Components

Python modular monolith with FastAPI and shared offline/online features. SQLAlchemy persistence; SQLite supports a portable local launch, PostgreSQL is the Compose target. A single leased database worker performs bounded matching jobs. React/TypeScript workbench consumes the API. Training runs outside HTTP requests. Model artifacts are trusted local build outputs only.

Raw snapshots are immutable, excluded from Git, and described by hashes, acquisition timestamps, bounding boxes and source metadata. Normalized records preserve raw source fields and immutable versions. Sorted record IDs define unordered pairs. Proposals bind record versions, feature schema, model and policy. Review runs in a transaction with optimistic stale checks. Canonical fields retain selection rules and all member values.

Candidate retrieval combines spatial and lexical/address passes with bounded results; no global Cartesian matching. Review-only policy stays active until independent evidence supports automatic linking. Source identifiers and weak-label methods never enter features.

## Evaluation contract

SAME / DIFFERENT / UNCERTAIN labels are distinct from operational decisions. Human gold, research-reviewed, silver and synthetic evaluations remain separate. Entity/component grouping precedes pair splits. Validation selects configuration; test is evaluated after selection. Candidate recall is reported only over known positives; full recall and cluster quality need independent truth. Track precision, recall, PR-AUC, confusion counts, coverage, abstention and sample sizes. No production-quality claim follows from silver performance.
