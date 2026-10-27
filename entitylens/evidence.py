"""Human-readable observations, separate from model confidence or ground truth."""

from rapidfuzz.fuzz import ratio
from entitylens.features import norm, distance
from entitylens.identity import location_blockers


def describe_pair(a, b, proposal):
    signals = []
    warnings = []
    missing = []
    for field, label in [
        ("name", "Name"),
        ("address", "Address"),
        ("phone", "Business phone"),
    ]:
        absent = [r["id"] for r in (a, b) if not str(r.get(field) or "").strip()]
        if absent:
            missing.append(
                dict(
                    field=field,
                    message=f"{label} unavailable in {len(absent)} source record(s)",
                    records=absent,
                )
            )
    na, nb = norm(a.get("name")), norm(b.get("name"))
    if na and nb:
        if na == nb:
            signals.append("Names agree after normalization")
        elif ratio(na, nb) < 50:
            warnings.append(
                "Names differ substantially; investigate a rename or separate businesses"
            )
    aa, ab = norm(a.get("address")), norm(b.get("address"))
    if aa and ab and aa == ab:
        signals.append("Street addresses agree after normalization")
    pa, pb = a.get("phone"), b.get("phone")
    if pa and pb:
        if pa == pb:
            signals.append(
                "Business phone agrees; a shared chain phone does not establish branch identity"
            )
        else:
            warnings.append("Business phones differ")
    meters = distance(a, b)
    if meters is None:
        missing.append(
            dict(
                field="coordinates",
                message="Distance unavailable: one or both coordinate pairs are missing or invalid",
                records=[r["id"] for r in (a, b)],
            )
        )
    elif meters <= 50:
        signals.append(
            "Source coordinates are within 50 m; colocated businesses may still differ"
        )
    conflicts = location_blockers([a, b])
    model = proposal.get("model")
    disagreement = (
        abs(proposal["score"] - proposal.get("baseline", proposal["score"]))
        if model
        else None
    )
    if disagreement is not None and disagreement >= 0.25:
        warnings.append(
            "Model and rule scores disagree; compare the source evidence carefully"
        )
    return dict(
        distance_m=round(meters, 1) if meters is not None else None,
        signals=signals,
        warnings=warnings,
        missing=missing,
        conflicts=conflicts,
        score_disagreement=disagreement,
        basis="Current source records; scores remain bound to proposal record versions",
        model=model or "rule baseline",
        policy="review-only",
    )
