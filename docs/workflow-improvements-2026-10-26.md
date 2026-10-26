# Workflow improvements — 2026-10-26

## Product decisions

Prioritize analyst decisions and usable output over new infrastructure. The previous interface displayed a score but made the analyst infer missing evidence, location conflicts and review history. Improvements preserve the existing classifier and review-only policy.

### Explain observations before decisions

The assessment panel shows distance in meters, normalized name/address agreement, business-phone observations, missing fields, and model/rule disagreement. These are observed facts and heuristic warnings, not feature attributions, calibrated probabilities or ground truth. Numeric proposal features remain available in an expandable section.

Preview and confirmation now share the same full-group merge blockers: cannot-link, changed source/group, size limit, street number/suffix, unit and geographic separation. Same place is disabled while blockers exist. Different places and Unsure remain available for current undecided proposals. All writes still revalidate context/revision/version transactionally; preview is not authorization to bypass a later conflict.

### Find difficult cases

Queue order supports highest score and model/rule disagreement. The latter ranks absolute score differences for trained-model proposals; rule-only proposals do not pretend to have model disagreement. This is a triage heuristic, not uncertainty calibration or active-learning performance evidence. Search now includes both names, both street addresses and pair IDs, with literal Unicode casefold matching and a 200-character bound.

### Reopen and trace decisions

History shows immutable reviewed names, date, rationale and pair reference. Open pair fetches by exact ID independently of queue pagination or status filters. The local #pair=ID permalink survives reload. Return to queue restores the current queue. If a legacy decision lacks preserved historical payloads, its names are explicitly unavailable rather than invented from current source values.

### Export an auditable directory

Entities offers JSON and CSV downloads. JSON includes field provenance and immutable record versions; CSV is a flat directory with membership references. Changed entities are excluded from both. API export accepts limit <=500 and offset; JSON provides total/next_offset and CSV provides total/excluded count headers. The UI explicitly caps a download at 500 entities. Export reads one consistent canonical snapshot.

CSV uses standard quoting and neutralizes untrusted string formulas beginning with =, +, -, @, tab or line breaks, including leading whitespace. Numeric coordinates remain numeric. Export is bounded local output, not an unrestricted ingestion/upload workflow.

## Verification

- 46 pytest checks pass, including existing update/lease/constraint regressions and new assessment, immutable history, direct lookup, disagreement ordering, address search, pagination, formula escaping and stale-export tests.
- TypeScript and production build pass.
- A small warm local HTTP sample (five requests per endpoint, concurrency 1) measured median ~167 ms for score ordering, ~185 ms for disagreement ordering and ~109 ms for group preview. Full samples and limits are in reports/workflow-latency-2026-10-26.json; this is not a throughput or production-load claim.
- Browser: checked Temple Court assessment (6.9 m), switched to disagreement triage, observed the 135C/135 street-number blocker for Parcelle and disabled Same place.
- Browser: provisional Temple Court confirmation produced a canonical entity; CSV and JSON buttons downloaded files, and their content/provenance were inspected locally. Open pair from history and reload restored the exact reviewed pair despite its absence from the pending queue. Verification decision was undone, leaving zero active test decisions.
- Model, feature transformations, labels, splits and reported ML metrics were not retrained or retuned for this change.

The independent-gold, public deployment/authentication, PostgreSQL, stable canonical ID and hosted CI limitations remain unchanged. Tests establish these contracts, not production matching accuracy.
