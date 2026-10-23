# Data card

Domain: publicly observable food and drink establishments, Lower Manhattan. Two independently published catalogs: Overture Places 2026-10-21.0 and NYC DOHMH public inspection dataset. Raw snapshots stay local; manifests carry SHA-256 and acquisition query. `reports/data-quality.json` contains measured counts and missingness.

NYC repeated inspections collapse by CAMIS, newest inspection row first. This selection is a practical catalog view, not a comprehensive temporal history. Overture filters on the food_and_drink taxonomy hierarchy. Names and street numbers are preserved, Unicode case folding provides additional comparison forms. Raw business fields remain available locally. Coordinates are WGS84, distances use haversine meters.

7,118 records: 2,222 NYC and 4,896 Overture; 66,660 candidate pairs. Candidate reduction is 0.99387 against all cross-source pairs. Candidate recall is unknown without independently verified matches including outside retrieved candidates. Top-30 retrieval truncates per NYC record; future recall studies must account for truncation.

Current labels: automatic silver, positive on strong name/address/house/spatial agreement; negative on clearly dissimilar name and address/proximity. Ambiguous pairs are excluded. This creates an easier and biased evaluation distribution. Geographic longitude holdout excludes crossing pairs and guarantees record disjointness; it does not prove latent entity disjointness across boundaries. The absence of independently adjudicated entities prevents a sealed entity-disjoint gold claim.

Do not claim production accuracy, reviewer time savings or cluster quality from this dataset. Collect a second independently verified sample and outside-candidate searches before deploying automatic links.
