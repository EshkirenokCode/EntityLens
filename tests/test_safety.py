import json
import pytest
from concord import store
from concord.features import features, distance, candidates


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", str(tmp_path / "test.db"))
    store.init()
    records = [
        dict(
            id=k,
            name="Branch " + k,
            address="1 Main St",
            lat=40.7,
            lon=-74.0,
            phone="",
            version="v1",
            source=k,
        )
        for k in "ABC"
    ]
    with store.connect() as c:
        for r in records:
            c.execute("INSERT INTO records VALUES(?,?)", (r["id"], json.dumps(r)))
        for a, b in [("A", "B"), ("B", "C"), ("A", "C")]:
            p = dict(id=a + b, left=a, right=b, versions=["v1", "v1"], status="REVIEW")
            c.execute(
                "INSERT INTO pairs(id,payload) VALUES(?,?)", (a + b, json.dumps(p))
            )
    return records


def test_transitive_cannot_link(db):
    store.decide("AC", "DIFFERENT", "Separate branches", 1, "different-key")
    store.decide("AB", "SAME", "Same location", 1, "same-ab-key")
    with pytest.raises(ValueError, match="Cannot-link"):
        store.decide("BC", "SAME", "Tempting transitive merge", 1, "same-bc-key")
    with store.connect() as c:
        assert c.execute("SELECT count(*) FROM decisions").fetchone()[0] == 2


def test_undo_idempotency_stale(db):
    d = store.decide("AB", "SAME", "Matching address", 1, "stable-key")
    assert (
        store.decide("AB", "SAME", "Matching address", 1, "stable-key")["id"] == d["id"]
    )
    with pytest.raises(ValueError, match="Idempotency"):
        store.decide("AB", "DIFFERENT", "No", 1, "stable-key")
    store.undo(d["id"])
    with store.connect() as c:
        assert all(len(g) == 1 for g in store.components(c)[0])
    with pytest.raises(ValueError, match="Stale"):
        store.decide("AB", "SAME", "Old revision", 1, "new-stale-key")


def test_changed_source(db):
    with store.connect() as c:
        r = db[0]
        r["version"] = "v2"
        c.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(r), "A"))
    with pytest.raises(ValueError, match="Source changed"):
        store.decide("AB", "SAME", "Old source", 1, "changed-key")


def test_missing_geo_and_branches():
    a = dict(id="a", name="Cafe 2", address="5 Main St", lat=40.0, lon=-74.0, phone="")
    b = dict(
        id="b", name="Cafe 2", address="15 Main St", lat=40.001, lon=-74.0, phone=""
    )
    assert 110 < distance(a, b) < 112
    assert features(a, b)[3] == 0
    b["lat"] = None
    assert features(a, b)[7] == 1
    assert distance(a, b) is None


def test_retrieval_without_coordinates():
    a = dict(id="a", name="Unusual Cafe", address="", lat=None, lon=None, phone="")
    b = dict(a, id="b")
    assert len(list(candidates([a], [b]))) == 1


def test_different_street_numbers_block_merge(db):
    with store.connect() as c:
        r = dict(db[1], address="12 Main St")
        c.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(r), "B"))
    with pytest.raises(ValueError, match="street numbers"):
        store.decide(
            "AB", "SAME", "Same chain phone is insufficient", 1, "branch-guard-key"
        )


def test_shared_address_does_not_force_match(db):
    store.decide(
        "AB",
        "DIFFERENT",
        "Distinct businesses in same building",
        1,
        "shared-address-key",
    )
    with store.connect() as c:
        assert all(len(g) == 1 for g in store.components(c)[0])
