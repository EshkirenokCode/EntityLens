# Labeling guide

Label one physical establishment at one location. Open the pair in Review and inspect both raw names, addresses, coordinates, missing fields and available business evidence. Do not infer identity from a network brand, shared phone or shared building alone.

- SAME: evidence supports the same establishment at the same location. Record the evidence and its date.
- DIFFERENT: distinct branches, units or businesses. Record the conflicting evidence.
- UNCERTAIN: missing information, possible relocation or ambiguous renaming. Preserve the ambiguity.

Each annotation needs unordered pair ID, immutable record versions, rationale, evidence references, author/method, timestamp and provenance. UI decisions are local analyst decisions, not automatically independent gold. `reports/label-queue.json` is an unlabeled reproducible stratified sample. Its challenge strata must not estimate population prevalence. Random sampling and outside-retrieval searches need separate denominators.

Gold requires independent human checking and adjudication of disagreements. Research-reviewed labels and automatic silver labels remain separate. Synthetic cases never enter real evaluation. Analysts must verify external references themselves; the server does not fetch arbitrary imported URLs.

Examples: identical name and address in two catalogs is plausible SAME but still needs corroboration; the same coffee chain on adjacent streets is DIFFERENT; two restaurants in one hotel may be DIFFERENT; a renamed location without temporal evidence is UNCERTAIN. An unmatched source record is valid.
