# Data sources

Access checks: 2026-10-24. Acquisition parameters, hashes and timestamps live in `data/manifests`. Full source payloads are excluded from Git.

## Overture Places

[Guide](https://docs.overturemaps.org/guides/places/) · [Attribution](https://docs.overturemaps.org/attribution/)

Release inspected: 2026-10-21.0. Places is an already conflated catalog, not independent supplier observations. Preserve source references and apply the source-specific license: current documentation lists CDLA Permissive 2.0, Apache 2.0 and CC0 suppliers. Existence confidence is not a pair match probability. Attribution: Overture Maps Foundation, overturemaps.org, and suppliers recorded in each snapshot. Re-download raw data rather than publishing an unreviewed extract.

## NYC DOHMH Restaurant Inspection Results

[Dataset](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j) · [API](https://data.cityofnewyork.us/resource/43nn-pn8j.json) · [NYC terms](https://www.nyc.gov/home/terms-of-use.page)

Publisher: NYC Department of Health and Mental Hygiene. Public API responded without credentials. `camis` identifies establishments; repeated inspection rows are deduplicated before matching. They do not constitute independent catalogs. Inspection dates are not establishment creation dates; the 1900-01-01 sentinel means no valid inspection date. Retrieval time and source record date remain separate.

NYC portal terms and dataset disclaimers must accompany use; no additional dataset-specific license was exposed in the metadata probe. Raw redistribution remains disabled pending explicit terms review. Business contacts are used locally for comparisons; no personal contact enrichment.

## Scope and truth

Lower Manhattan bbox [-74.012, 40.710, -73.985, 40.730]. Catalog publication pipelines are independent; overlap in underlying public information is possible. Neither source supplies independent pair truth. Silver labels are research aids, never human gold. Synthetic fixtures are isolated from real-source evaluation.
