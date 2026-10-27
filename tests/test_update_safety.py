import json, time
import pytest
from entitylens import store


@pytest.fixture
def sample(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", str(tmp_path / "updates.db"))
    store.init()
    records = [
        dict(
            id=k,
            name="Cafe",
            address="1 Main",
            lat=40.0,
            lon=-74.0,
            source="nyc" if k == "a" else "overture",
            version="v1",
            phone="",
        )
        for k in "abc"
    ]
    with store.connect() as c:
        for r in records:
            c.execute("INSERT INTO records VALUES(?,?)", (r["id"], json.dumps(r)))
        for a, b in [("a", "b"), ("b", "c")]:
            p = dict(
                id=a + b,
                left=a,
                right=b,
                status="REVIEW",
                versions=["v1", "v1"],
                features=[1] * 8,
                score=0.9,
                baseline=0.9,
            )
            c.execute(
                "INSERT INTO pairs(id,payload) VALUES(?,?)", (a + b, json.dumps(p))
            )
    return records


def test_group_change_invalidates_preview(sample):
    with store.connect() as c:
        token = store.review_context(c, "ab")["context_version"]
    store.decide("bc", "SAME", "Same branch", 1, "another-link")
    with pytest.raises(ValueError, match="Group changed"):
        store.decide(
            "ab", "SAME", "Previewed earlier", 1, "old-group-key", context_version=token
        )


def test_canonical_keeps_reviewed_values_when_source_changes(sample):
    store.decide("ab", "SAME", "Reviewed values", 1, "first-link")
    with store.connect() as c:
        b = dict(sample[1], name="New business", version="v2")
        c.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(b), "b"))
        groups, rs = store.components(c)
        historical, changed = store.reviewed_members(c, ["a", "b"], rs)
    assert historical["b"]["name"] == "Cafe"
    assert changed == ["b"]


def test_worker_rejects_record_change_during_matching(sample, monkeypatch):
    from entitylens import worker

    def racing(left, right):
        with store.connect() as c:
            row = dict(sample[0], version="v2")
            c.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(row), "a"))
        yield left[0], right[0], [1] * 8, 0.9

    monkeypatch.setattr(worker, "candidates", racing)
    monkeypatch.setattr(worker, "score_pairs", lambda *args: None)
    with store.connect() as c:
        c.execute(
            "INSERT INTO jobs(id,status,created) VALUES('race','queued',?)",
            (time.time(),),
        )
    worker.tick()
    with store.connect() as c:
        job = c.execute("SELECT * FROM jobs WHERE id='race'").fetchone()
        assert job["status"] == "queued" and "Source changed" in job["error"]
        assert c.execute("SELECT count(*) FROM pairs").fetchone()[0] == 2


def test_house_suffix_conflict_is_not_hidden(sample):
    with store.connect() as c:
        for k, address in [("a", "12A Main St"), ("b", "12B Main St")]:
            r = dict(sample[0 if k == "a" else 1], address=address)
            c.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(r), k))
    with pytest.raises(ValueError, match="street numbers"):
        store.decide("ab", "SAME", "Same chain but separate units", 1, "suffix-branch")


def test_unit_conflicts_block_same_address(sample):
    with store.connect() as c:
        for i, unit in [(0, "Suite 1"), (1, "Suite 2")]:
            r = dict(sample[i], address="1 Main St " + unit)
            c.execute(
                "UPDATE records SET payload=? WHERE id=?", (json.dumps(r), r["id"])
            )
    with pytest.raises(ValueError, match="units"):
        store.decide("ab", "SAME", "Shared building is insufficient", 1, "unit-branch")


def test_changed_member_blocks_extending_old_group(sample):
    store.decide("ab", "SAME", "Original branch", 1, "review-before-change")
    with store.connect() as c:
        r = dict(sample[0], version="v2", name="New occupant")
        c.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(r), "a"))
    with pytest.raises(ValueError, match="changed source records"):
        store.decide(
            "bc", "SAME", "Cannot silently extend stale group", 1, "extend-stale-group"
        )


def test_worker_retires_removed_candidates(sample, monkeypatch):
    from entitylens import worker

    monkeypatch.setattr(worker, "candidates", lambda *args: iter([]))
    monkeypatch.setattr(worker, "score_pairs", lambda *args: None)
    store.decide("bc", "DIFFERENT", "Preserved human decision", 1, "preserve-rejection")
    with store.connect() as c:
        c.execute(
            "INSERT INTO jobs(id,status,created) VALUES('retire','queued',?)",
            (time.time(),),
        )
    worker.tick()
    with store.connect() as c:
        ps = {r["id"]: r for r in store.rows(c, "pairs")}
        assert ps["ab"]["status"] == "RETIRED"
        assert ps["bc"]["status"] == "DIFFERENT"


def test_worker_does_not_publish_after_lease_expiry(sample, monkeypatch):
    from entitylens import worker

    moment = [1000.0]
    monkeypatch.setattr(worker.time, "time", lambda: moment[0])

    def slow(left, right):
        moment[0] = 1400.0
        yield left[0], right[0], [1] * 8, 0.9

    monkeypatch.setattr(worker, "candidates", slow)
    monkeypatch.setattr(worker, "score_pairs", lambda *args: None)
    with store.connect() as c:
        c.execute("INSERT INTO jobs(id,status,created) VALUES('expired','queued',1)")
    worker.tick()
    with store.connect() as c:
        row = c.execute("SELECT status,error FROM jobs WHERE id='expired'").fetchone()
        assert row["status"] == "queued" and "lease" in row["error"]
        assert c.execute("SELECT count(*) FROM pairs").fetchone()[0] == 2
