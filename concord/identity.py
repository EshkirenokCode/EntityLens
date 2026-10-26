"""Observed location conflicts shared by preview and confirmation; not model truth."""

import re
from itertools import combinations
from concord.features import distance


def location_blockers(records):
    findings = []
    for a, b in combinations(records, 2):
        addresses = [(r.get("address") or "").strip().casefold() for r in (a, b)]
        houses = [re.match(r"^(\d+(?:-\d+)?[a-z]?)\b", s) for s in addresses]
        units = [
            re.search(
                r"(?:\b(?:suite|unit|ste|apt|apartment)\.?\s*#?\s*|#\s*)([a-z0-9-]+)\b",
                s,
            )
            for s in addresses
        ]
        ids = [a["id"], b["id"]]
        if all(houses) and houses[0][1] != houses[1][1]:
            findings.append(
                dict(
                    code="street_number",
                    message="Conflicting street numbers: resolve source evidence before merging branches",
                    records=ids,
                )
            )
        if all(units) and units[0][1] != units[1][1]:
            findings.append(
                dict(
                    code="unit",
                    message="Conflicting units: shared building does not establish branch identity",
                    records=ids,
                )
            )
        meters = distance(a, b)
        if meters is not None and meters > 300:
            findings.append(
                dict(
                    code="distance",
                    message="Conflicting coordinates exceed the location safety limit (300 m)",
                    records=ids,
                )
            )
    return findings
