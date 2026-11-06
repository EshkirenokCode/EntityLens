# Interface review, 6 November 2026

The review screen now uses a top navigation bar and a wider comparison area. The old workspace switcher, owner profile and repeated counters took space without helping a place-matching decision. Source names and the Lower Manhattan scope remain beside the page heading on desktop.

Source fields stay aligned in a table. The queue uses separate scrolling, and the decision footer stays visible. Typography distinguishes page headings, place names, field labels and numeric values. Text contrast was increased, and source differences retain their own highlight.

Interface copy now describes actions and data. Source checks explain matching names, addresses, phones and coordinates in shorter sentences. Scores remain explicitly uncalibrated. The model results page explains that the labels come from rules and that independent matching accuracy is still unmeasured.

The disagreement queue displays the absolute difference between model and rule scores. Its display uses the same saved pair scores as the existing sort. For a rule-only pair, the gap is unavailable. This changes presentation only.

A Write a reason control focuses the required note. Blocked links show their first reason beside the disabled action. The note, group checks, stale-record checks and existing decision validation still apply. On a phone, opening a pair and returning to the queue reset page scrolling. The action footer leaves room for the last fields and checklist.

## Verification

- 48 Python tests passed. The existing Starlette TestClient dependency deprecation warning remains.
- TypeScript and the production frontend build passed.
- Browser checks covered note validation, clearing an unsaved note on selection, disagreement ordering and its displayed gap, blocked links, empty search, source views, model results, named history, direct-link reload and J/K navigation.
- Actual inspected viewports were 1280 by 720, 536 by 988 and 390 by 844. The inspected screens had no horizontal document overflow. The phone view starts at the top and keeps decision buttons in the viewport.
- No review decision was added. Training data, trained artifacts and evaluation metrics were not changed.

[Desktop](screenshots/review-desktop-2026-11-06.png), [phone](screenshots/review-phone-2026-11-06.png), [blocked link](screenshots/review-conflict-2026-11-06.png).

These checks cover the local application and the inspected sizes. They do not establish a complete cross-browser accessibility audit.
