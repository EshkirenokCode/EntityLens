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


def coordinates(record):
    try:
        lat, lon = float(record["lat"]), float(record["lon"])
        if (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            return lat, lon
    except (TypeError, ValueError, KeyError):
        pass
    return None


def distance(a, b):
    first, second = coordinates(a), coordinates(b)
    if first is None or second is None:
        return None
    p, q = math.radians(first[0]), math.radians(second[0])
    d = q - p
    l = math.radians(second[1] - first[1])
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
        xy = coordinates(b)
        if xy is not None:
            grid.setdefault((int(xy[0] / 0.003), int(xy[1] / 0.003)), []).append(b)
        for t in set(norm(b["name"]).split()):
            if len(t) > 3:
                tokens.setdefault(t, []).append(b)
    for a in left:
        pool = {}
        xy = coordinates(a)
        if xy is not None:
            x, y = int(xy[0] / 0.003), int(xy[1] / 0.003)
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
