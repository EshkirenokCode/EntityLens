# Correctness audit — 2026-10-25

The previous passing suite did not exercise source updates during jobs, changing group previews, or historical canonical values. New regressions reproduced failures before the fixes; these were functional correctness problems, not cosmetic differences.

## Corrected behavior

- A matching job now verifies the complete input record-version snapshot and its lease immediately before publication. Source drift rolls back the batch and schedules a bounded retry; expired or cancelled work cannot publish.
- Pending candidates omitted by a new retrieval run become RETIRED. Accepted decisions are preserved, rather than overwritten or mixed with current candidates.
- Every review stores immutable record payloads in decision_records. Canonical fields use reviewed payloads. Source changes flag the entity for review and exclude it from normal export. Legacy records are backfilled only from matching versions; missing evidence is explicitly unavailable.
- Review requests require context_version from the group impact endpoint. Membership, affected record versions and active decisions enter the fingerprint. A changed group returns 409. This closes the race between preview and confirmation.
- Extending a group with changed members is blocked until affected links are undone and reevaluated.
- House-number suffixes (12A/12B) and explicit unit differences (Suite 1/Suite 2) cannot be merged solely because the building/brand matches.
- Completed jobs reject cancel and retry with 409. Unknown jobs return 404. Cancellation remains idempotent for cancelled jobs.
- Unicode casefold search fixes non-ASCII case matching.
- Invalid, incomplete, nonfinite and out-of-range coordinates no longer crash retrieval or produce a false finite distance. Lexical retrieval remains available when geography is missing.
- Equal classifier scores now use the transparent lexical/spatial baseline as a secondary ordering key instead of arbitrary pair IDs. No model predictions or evaluation labels changed.
- Review defaults to Needs review with explicit processed-state filters. Saving a decision advances the pending queue; Undo restores the pair. Empty last pages are corrected after the queue shrinks.
- Decisions are disabled until the group preview loads. Preview failures have a retry state. Navigation is locked while saving, and unchanged network retries reuse the same idempotency key.
- Source changes are visible on proposals and canonical entities. The misleading raw-value Conflict badge is now Source values differ.
- Local API and worker were stopped during the audit. The combined make dev launcher now starts both with the same project-relative entitylens-v1.db, supervises failures and stops children on exit. Existing entitylens.db files are preserved and selectable through ENTITYLENS_DB.

## Verification

33 pytest checks pass, including HTTP contracts and regression cases for group changes, source-change races, historical fields, stale exports, removed candidates, lease expiry, unit conflicts and terminal job states. TypeScript and production frontend build pass. One installed Starlette TestClient deprecation warning remains.

Feature values were recomputed for all 66,660 existing real candidate pairs and agree with saved values within 1e-12. No classifier was retrained or selected against the holdout during this work.

Browser check on the real local data: review submitted with current context, pending queue changed from 66,660 to 66,659, reviewed entity appeared, and Undo returned the count to zero active decisions while preserving history. The verification annotation was explicitly provisional and undone. Local combined launcher was tested on a second port and shut down; the primary app is running through make dev.

## Scope

These checks establish the specific regression behavior; they are not proof of an error-free product. Independent gold/model accuracy, PostgreSQL support, external canonical ID stability, public authorization/session isolation and Docker/hosted CI verification remain open. The coordinate panel remains a schematic, not a map tile provider.
