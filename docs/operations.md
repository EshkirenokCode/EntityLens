# Operations

## Local launch

Python 3.12+, Node 22+. `make setup`, `make data`, `make train`, `make web`, `make dev`. The combined launcher supervises API and worker with the same database; Ctrl+C stops both. Separate `make run` / `make worker` remain available. The default database is project-relative concord-v1.db; older concord.db files are preserved and can be selected explicitly with CONCORD_DB. UI: http://127.0.0.1:8765 . OpenAPI: /docs. No cloud account or API key required. The downloader pins Overture release 2026-10-21.0. The NYC endpoint is live: a new download is a new snapshot, not a guarantee of reproducing an older payload. Preserve original hashed files to reproduce the exact experiment.

SQLite WAL is the implemented storage backend, shared by one API and one worker on one machine. SQL schema creation is idempotent in store.init. PostgreSQL/PostGIS, SQLAlchemy migrations and distributed workers remain future deployment work; they are not implemented support. Docker Compose is provided for the implemented SQLite deployment and has not been executed in this environment because Docker is unavailable.

The API binds loopback locally. Do not expose this administrative workspace directly to the Internet. It has no authentication or visitor session isolation. Training and imports are local commands. A public demo needs authenticated administration, isolated writable visitor state, ingress limits, HTTPS and read-only benchmark datasets before exposure.

## Source updates and decisions

After obtaining and preparing a new snapshot, run `.venv/bin/python scripts/import_snapshot.py`, then queue a matching run. Every overwritten source record version is retained. Pending proposals bind source versions and reject stale confirmations. Matching refreshes pending proposals, incrementing revisions; accepted decisions stay untouched. Source-change audit events preserve the before/after versions. Missing records never imply closure. Historical source changes must be manually reviewed before relying on accepted membership; there is no automatic change adjudication.

Review uses BEGIN IMMEDIATE transactions, revision checks and idempotency keys. Cannot-link constraints are checked across complete connected groups. Different house numbers, more than 300m separation and groups above 12 members block a merge. These conservative guards may reject valid noisy matches; correct source evidence before proceeding. Undo is an additional event. Entity IDs currently derive from a deterministic minimum member and can change when membership changes; durable externally referenced canonical IDs are not yet supported.

## Worker

Jobs persist in the database. Claim is transactional, lease lasts 300 seconds, at most three attempts. Restart recovers expired jobs. Cancellation clears the lease; publication checks ownership and commits all candidate updates in one transaction. Completed/failed jobs can be inspected in Sources & Runs; failed/cancelled jobs can be retried. Matching must finish within the fixed lease; large runs require lease heartbeats before scaling. Do not run parallel workers with this local profile.

## Registry and rollback

Run `scripts/registry.py register`, then `evaluate --version VERSION`, then `activate --version VERSION`. Evaluation checks the saved data/split manifest. Activation remains review-only and does not certify independent accuracy. `rollback` restores the previous immutable model and accompanying manifest. Registry retains hashes and states candidate → evaluated → active → retired. Shared inference rejects incompatible feature schema. Models are trusted locally built artifacts; never accept arbitrary pickle uploads. Keep model, feature code, dependency lock and data manifests together when rolling back; schema changes require compatible code checkout.

## Monitoring, backups and recovery

/api/monitoring exposes score histogram, review count and job errors. /api/status exposes input missingness. Drift is a signal, not evidence of accuracy loss. Do not automatically retrain or promote on drift. HTTP measurements are in reports/http-benchmark.json; they do not measure batch throughput or user time savings.

Back up SQLite using Python sqlite3.Connection.backup while live, or stop API/worker and copy database together with raw manifests, snapshots and model registry. Do not copy a WAL database file alone while writers run. Test restoration on a separate database path via CONCORD_DB. No external infrastructure or production server has been modified.

## CI

Local checks: `make test`. `docs/ci.yml.template` contains the intended GitHub Actions workflow. The current repository token cannot create files under .github/workflows because it lacks workflow scope; move the template there once authorized credentials support it. No successful hosted CI run is claimed.

## Record and group safety update — 2026-10-25

Review API requests require context_version from the impact endpoint. It binds the affected membership, source versions and active decisions; a changed context returns 409. Missing context returns 422. The UI disables submission until preview loads. Failed network requests retain the same idempotency key for an unchanged intent.

Confirmation saves immutable record payloads in decision_records. Canonical fields use those reviewed payloads. If a current source version changes, the entity is marked needs_review and excluded from normal export; historical values remain visible. Missing legacy historical payloads are explicitly marked unavailable, rather than reconstructed as reviewed current data. Undo affected links and rerun matching to investigate the new versions.

The worker validates source versions and lease expiry before publishing. Candidates no longer returned are retired from the pending queue; accepted decisions remain intact. Jobs cannot falsely report successful retries/cancellation of completed work. Street-number suffixes and explicit unit identifiers are checked conservatively during merging.
