# Design and reliability audit — 2026-10-24

## Findings corrected

1. SQLite connection context managers committed transactions without closing handles. The shared connection helper now closes in finally, preserving transaction rollback; a regression verifies the closed handle.
2. Pair pagination deserialized and sorted every candidate in application memory. Filtering, ordering and limit/offset now run in SQLite; only returned records are decoded. A five-request warm run returned a 143ms median for 40 candidates. This is a local measurement, not a load guarantee.
3. Component reconstruction loaded all candidate pairs even without decisions. It now loads only pairs referenced by active decisions.
4. Search responses could arrive out of order. A request generation check discards superseded responses; input is debounced.
5. Keyboard navigation could carry an evidence note to a different pair, and empty queues could produce a negative index. Notes reset on pair change and indices are clamped.
6. During pending refreshes, old comparison content could remain actionable. Decision buttons now disable while loading.
7. Rounded scores resembled 100% certainty. Display uses decimal model score with the existing calibration warning.
8. Unknown job cancel/retry returned success. They now return 404; retries reject an already active run. Queue creation is serialized in a database transaction.
9. Matching status required manual refresh; Sources & Runs now polls every two seconds and action errors surface in the interface.
10. Low-contrast decorative styling and external fonts weakened usability. The new neutral/slate/blue interface uses local system fonts, stronger field hierarchy, smaller counters and accessible navigation labels. Decorative roads were removed from the coordinate schematic.

## Verification passes

- Initial pass: code inspection, source/label limitations, visual reference research, baseline 11 tests and production build.
- Second pass: added HTTP contract tests; 16 tests passed, TypeScript and production build passed; desktop/narrow layouts inspected, empty search and 0–0 pagination confirmed in browser.
- Third pass: full 16-test suite rerun and production build passed; repeated warm HTTP measurements saved; final source diff and portfolio claims reviewed. No classifier training or holdout-based tuning was performed during this polish.

The tests emit one installed Starlette TestClient deprecation warning. This is not hidden or treated as a product failure. Hosted CI and Docker execution remain unverified. Browser testing is manual and covers the available Chromium surface, not every browser, device or assistive technology.

## Remaining limitations

Independent gold, true entity-disjoint evaluation, outside-retrieval recall, public authentication/session isolation, PostgreSQL/PostGIS and stable external canonical IDs remain open. Registry compatibility remains feature-schema based; complete environment rollback requires restoring compatible code and dependencies. Scores on ambiguous renamings can be high; review-only policy is essential.

## Portfolio assessment

Show the source-to-review-to-provenance workflow, regression checks and honest experiment analysis as a local ML engineering case study. Include the negative SVD result and the limits of heuristic supervision. Do not present perfect silver scores as demonstrated real accuracy, the coordinate schematic as a production map, or Compose/CI templates as tested infrastructure. A publicly writable anonymous demo is not ready for exposure.
