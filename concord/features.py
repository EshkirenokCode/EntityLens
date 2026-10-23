import math, re, unicodedata
from rapidfuzz.fuzz import ratio, token_set_ratio

SCHEMA = "pair-v1"
NAMES = [
    "name_ratio",
    "name_tokens",
    "address_ratio",
    "house_equal",
    "distance_proximity",
    "phone_equal",
    "missing_phone",
    "missing_coordinates",
]


def norm(v):
    return " ".join(
        re.findall(r"\w+", unicodedata.normalize("NFKC", str(v or "")).casefold())
    )


def distance(a, b):
    if any(x.get(k) is None for x in (a, b) for k in ("lat", "lon")):
        return None
    p, q = math.radians(a["lat"]), math.radians(b["lat"])
    d = q - p
    l = math.radians(b["lon"] - a["lon"])
    return (
        6371008.8
        * 2
        * math.asin(
            min(
                1,
                math.sqrt(
                    math.sin(d / 2) ** 2
                    + math.cos(p) * math.cos(q) * math.sin(l / 2) ** 2
                ),
            )
        )
    )


def features(a, b):
    n, m = norm(a["name"]), norm(b["name"])
    x, y = norm(a["address"]), norm(b["address"])
    d = distance(a, b)
    house = lambda s: re.match(r"^\d+[a-z]?", s)
    h, k = house(x), house(y)
    pa, pb = a.get("phone", ""), b.get("phone", "")
    return [
        ratio(n, m) / 100,
        token_set_ratio(n, m) / 100,
        ratio(x, y) / 100,
        float(bool(h and k and h[0] == k[0])),
        math.exp(-d / 100) if d is not None else 0,
        float(bool(pa and pb and pa == pb)),
        float(not pa or not pb),
        float(d is None),
    ]


def baseline(f):
    return 0.45 * f[0] + 0.25 * f[2] + 0.2 * f[4] + 0.1 * f[5]


def candidates(left, right, limit=30):
    # Spatial grid and lexical inverted index avoid a catalog Cartesian join.
    grid = {}
    tokens = {}
    for b in right:
        if b.get("lat") is not None:
            grid.setdefault((int(b["lat"] / 0.003), int(b["lon"] / 0.003)), []).append(
                b
            )
        for t in set(norm(b["name"]).split()):
            if len(t) > 3:
                tokens.setdefault(t, []).append(b)
    for a in left:
        pool = {}
        if a.get("lat") is not None:
            x, y = int(a["lat"] / 0.003), int(a["lon"] / 0.003)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    for b in grid.get((x + dx, y + dy), []):
                        pool[b["id"]] = b
        for t in set(norm(a["name"]).split()):
            if len(tokens.get(t, [])) <= 100:
                for b in tokens.get(t, []):
                    pool[b["id"]] = b
        ranked = sorted(
            ((baseline(f := features(a, b)), b, f) for b in pool.values()),
            key=lambda z: (-z[0], z[1]["id"]),
        )
        for score, b, f in ranked[:limit]:
            yield a, b, f, score
