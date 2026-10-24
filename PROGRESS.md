# Progress — 2026-10-24

## Implemented and verified locally

- Architecture, identity policy, source attribution, labeling and evaluation contract, ADRs.
- Independent real NYC DOHMH and Overture snapshots with SHA-256 manifests; repeated inspections deduplicated by CAMIS.
- 7,118 food establishment records and 66,660 spatial/lexical candidates. Input quality report saved.
- Persistent FastAPI/React workbench: source manifests, matching jobs, search, pair evidence, group impact preview, review, canonical provenance, decision history and undo.
- SQLite WAL transactions, idempotency, source/revision checks, full-component cannot-link checks, branch/location guards, leased worker, retry/cancellation and expired-lease recovery.
- Snapshot update command preserves old record versions and source-change audit events. Simulated source-version change is covered by regression test; no real second temporal snapshot is claimed.
- CPU gradient boosting training, train-only lexical SVD ablation, geographic record-disjoint manifests, validation selection, keyed predictions and explicit silver limitations.
- Local hashed model registry with evaluated/active states and rollback command; active review-only model registered.
- Monitoring endpoints and bounded export; single batch completed in 8.93 seconds; warm HTTP measurements saved separately.
- Browser verified: real pair display, provisional confirmation, canonical source lineage, undo and Evaluation screen. Narrow viewport inspected. Production frontend build and regression checks passed.
- Reproducible local commands, Docker/Compose definitions, operational guide and demo script.
- Stages pushed to the owner's GitHub with owner identity. No coauthor trailers.

## Evidence boundaries and remaining work

- No independent human gold. An 80-row stratified unlabeled queue is prepared. Silver perfect scores only establish reproduction of heuristic rules; ambiguous renamings can still rank highly.
- Geographic split proves record isolation, not adjudicated entity/component isolation. Build a new independently reviewed, entity-grouped sealed test before claims of matching accuracy. Outside-retrieval recall, cluster quality and independent calibration remain unmeasured.
- Review-only policy stays enabled. Neural multilingual encoder/fine-tuning is deferred pending adequate labels; SVD is not a neural encoder.
- Implemented storage is SQLite. PostgreSQL/PostGIS, Alembic migrations, durable external canonical IDs, public authentication/session isolation and lease heartbeats are not implemented.
- Docker is unavailable here, so Compose is unverified. No production deployment or paid resources created.
- GitHub token lacks workflow scope. Intended CI configuration is docs/ci.yml.template; hosted CI is not enabled.
- Browser testing covers the core flow and a narrow viewport, not a complete cross-browser/error-state accessibility audit. Coordinate display is a schematic, without external map tiles.

## Continue from here

Do not retrain/tune from the current holdout and call it a new sealed test. First adjudicate real entity groups and independent labels, including branches, shared premises, renamed businesses and missed candidates. Then finish PostgreSQL migration, stable entity identity and public-demo isolation, run full UI/error-state checks and enable hosted CI with appropriate credentials. The local v0.1 is operational; the full brief is not yet completed.

## Polish and audit — 2026-10-24

- Researched Dribbble reconciliation interfaces, Mobbin dashboard hierarchy, Linear design refresh and Refero reference availability; rationale saved in docs/design-research.md.
- Replaced decorative styling with a compact, neutral analyst workbench; removed network fonts, strengthened text hierarchy, clarified model scores and coordinate schematic.
- Fixed connection lifetime, search ordering, note carryover, empty navigation, stale actions during refresh, pagination performance and job lifecycle errors; added live run polling.
- Added HTTP integration coverage: 16 tests now pass. Two additional verification passes and production builds passed. One dependency deprecation warning is documented.
- Local warm pair-page median approximately 143ms for 40 records. No new model-quality claim.
- Full test walkthrough, five use cases and portfolio boundaries: docs/testing-guide.md. Findings and pass results: docs/polish-audit.md.

## Correctness follow-up — 2026-10-25

Reproduced and corrected source-version races, stale canonical values, mutable group previews, pending-candidate retirement, address suffix/unit conflicts, terminal job action responses, Unicode search, invalid geometry handling and pending review navigation. Immutable decision_records and required review context fingerprints added. Changed entities retain reviewed values and are excluded from normal export. Local startup unified with make dev and project-relative concord-v1.db.

33 tests and the production build pass; feature compatibility checked across all 66,660 real pairs without retraining. Browser confirmed submit → queue advance → canonical entity → undo. Full evidence: docs/correctness-audit-2026-10-25.md. Independent model quality and deployment limitations remain unchanged.
