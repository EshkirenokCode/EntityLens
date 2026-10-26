# Product walkthrough and test guide

## What is implemented

Independent NYC DOHMH inspection records are deduplicated by establishment ID. Overture food and drink records form the second catalog. Immutable snapshots and hashes feed normalization, bounded spatial/lexical retrieval, shared pair features, CPU-trained gradient boosting, manual review, constrained canonical membership and provenance. A local durable worker processes queued runs. Source updates, rollback, monitoring and evaluation commands are documented in operations.md.

The trained model learned silver supervision. Its perfect agreement with heuristic labels does not establish independent matching accuracy. Every live link requires analyst review.

## Quick test without downloading again

Open http://127.0.0.1:8765 . Existing local data has 7,118 records and 66,660 candidates. If the process stopped, launch `make dev` to start the API and worker together. Set the same CONCORD_DB for both processes. The current verified session uses `CONCORD_DB=concord-v1.db`.

1. Review: search for `New Shun Wei`, compare names, street address, business phone and coordinates. Expand Group impact. An empty evidence note must prevent saving.
2. Add a provisional evidence note and confirm Same place. Entities must show source values and lineage. Refresh: the decision persists.
3. Entities: Undo must remove that link, preserve history and return the proposal to review. Repeating undo is safe.
4. Search for a nonexistent place. Expect zero results and `0–0`, with no selected record. Clear the search and use J/K to switch pairs. Evidence notes must not carry to another pair.
5. Search `Chipotle` or `Starbucks`. A shared chain name is not evidence of one branch. Inspect addresses before recording Different places. Ambiguous evidence should remain Unsure.
6. Sources & Runs: inspect timestamps and SHA-256; queue one run. Status updates every two seconds. Cancel/retry are available for eligible states. A second queue request reuses an existing active run.
7. Evaluation: inspect baseline, gradient boosting and SVD ablation. The silver limitation and review-only policy must be visible.
8. Open `/docs` to inspect the API. `/api/export?limit=100` exports canonical entities. Limits above 500 are rejected. No independent gold is modified by UI decisions.

## Five practical use cases

| Use case | Current demonstration | Scope limit |
|---|---|---|
| Reconcile two restaurant catalogs | Compare NYC DOHMH against Overture, confirm the same location | Fixed prepared sources, not arbitrary catalog upload |
| Protect chain branches from false merges | Compare neighboring branch addresses, reject links | Conservative guards may require resolving noisy addresses |
| Investigate renaming or conflicting observations | Inspect original names, missing fields and coordinates; choose Unsure | Temporal succession is not established automatically |
| Build an auditable canonical directory | View field-level source values, contradictions and reversible membership | Entity IDs are not stable external identifiers yet |
| Evaluate a matching pipeline before adoption | Compare baseline and trained models; inspect manifests and supervision | Independent quality, retrieval recall and cluster metrics remain unproven |

## Automated checks

`make test` runs Python regressions and a TypeScript/production build. Tests use temporary databases and include transitive cannot-link, branch protection, stale source/revision, idempotency, undo, expired leases, split isolation, schema mismatch, HTTP pagination/search, job lifecycle and connection closure. `scripts/benchmark.py` runs bounded warm HTTP timings.

Docker/Compose and public deployment remain unverified. Hosted CI needs a GitHub credential with workflow scope; the workflow remains a template. A Starlette TestClient deprecation warning is currently emitted by installed dependencies; requests still pass.

## Additional regression checks — 2026-10-25

Review defaults to Needs review. Same/Different/Unsure filters expose processed pairs. A saved decision removes its pair from pending results; Undo restores it. Completed jobs reject retry and cancel (409). Unicode search supports casefold matching. A changed group context rejects an old confirmation, and changed source data cannot silently alter reviewed canonical values or enter normal export. The worker rejects results if records change during matching, retires removed pending candidates and refuses publication after lease expiry.

## New analyst tools — 2026-10-26

- Open Review and inspect What the sources tell us. Distance is in meters; agreement is supporting evidence, not match probability. Expand Numeric features when needed.
- Select Model / rule disagreement in Queue order to inspect conflicting scores. Search a street address or a pair ID as well as names. Blocked merges explain the actual shared safety checks before submission.
- Entities history shows the reviewed names and timestamp. Open pair works even when the pair is absent from the pending page. Reload the #pair=ID URL to return to it, or use Return to queue.
- Download JSON for full field provenance or CSV for a flat directory. Downloads include up to 500 eligible entities; changed entities are excluded. The export API supports offset/limit pagination for larger local directories. CSV formula-like strings are escaped as text.
