# ADR 003: reversible constrained membership

Accepted 2026-10-24. Preserve source records; derive confirmed membership from append-only decisions plus undo events. Validate the complete connected component against every active cannot-link. Use transactional writes and proposal revision/source checks. Conservative location and house-number guards prevent obvious branch merges. Cap components at 12 members for explicit investigation.

Do not impose one-to-one cardinality: independent catalogs can contain multiple records for one physical place. Canonical fields use stable source ordering with explicit value lineage and conflicts, rather than silently overwriting inputs. Entity identifiers currently derive from members and therefore are not persistent external identifiers. Introduce an entity registry before exposing durable external entity references.
