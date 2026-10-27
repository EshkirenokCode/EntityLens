import json, sqlite3
import pytest
from entitylens import store


def test_page_and_literal_search(client):
    r = client.get("/api/pairs", params={"q": "100%", "limit": 1}).json()
    assert r["total"] == 1 and r["items"][0]["a"]["name"] == "Cafe 100%"
    assert client.get("/api/pairs?offset=1").json()["items"] == []
    assert client.get("/api/pairs?q=absent").json()["total"] == 0
    assert client.get("/api/pairs?limit=1000").status_code == 422


def test_review_and_stale_http(client):
    payload = dict(
        kind="SAME",
        rationale="Source comparison only",
        revision=1,
        idempotency_key="http-stable-key",
        context_version=client.get("/api/pairs/ab/impact").json()["context_version"],
    )
    r = client.post("/api/pairs/ab/decision", json=payload)
    assert r.status_code == 200
    assert (
        client.post("/api/pairs/ab/decision", json=payload).json()["id"]
        == r.json()["id"]
    )
    assert len(client.get("/api/entities").json()) == 1
    assert client.post("/api/decisions/" + r.json()["id"] + "/undo").status_code == 200
    assert client.get("/api/entities").json() == []
    payload["idempotency_key"] = "http-stale-key"
    assert client.post("/api/pairs/ab/decision", json=payload).status_code == 409


def test_jobs_and_errors(client):
    a = client.post("/api/jobs").json()["id"]
    assert client.post("/api/jobs").json()["id"] == a
    assert client.post("/api/jobs/unknown/cancel").status_code == 404
    assert client.post("/api/jobs/unknown/retry").status_code == 404
    assert client.post("/api/jobs/" + a + "/cancel").status_code == 200
    assert client.post("/api/jobs/" + a + "/retry").status_code == 200
    assert client.post("/api/jobs/" + a + "/retry").status_code == 409


def test_impact_and_exports(client):
    assert len(client.get("/api/pairs/ab/impact").json()["members"]) == 2
    assert client.get("/api/pairs/absent/impact").status_code == 404
    assert client.get("/api/export?limit=0").status_code == 422
    assert client.get("/api/monitoring").json()["candidate_count"] == 1


def test_connections_close(client):
    with store.connect() as c:
        c.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        c.execute("SELECT 1")


def test_finished_job_actions_are_not_successful(client):
    with store.connect() as c:
        c.execute(
            "INSERT INTO jobs(id,status,created) VALUES('finished','completed',0)"
        )
    assert client.post("/api/jobs/finished/retry").status_code == 409
    assert client.post("/api/jobs/finished/cancel").status_code == 409


def test_missing_preview_context_rejected(client):
    r = client.post(
        "/api/pairs/ab/decision",
        json=dict(
            kind="SAME",
            rationale="No preview",
            revision=1,
            idempotency_key="missing-preview",
        ),
    )
    assert r.status_code == 422


def test_unicode_search(client):
    with store.connect() as c:
        r = json.loads(
            c.execute("SELECT payload FROM records WHERE id='a'").fetchone()[0]
        )
        r["name"] = "CAFÉ STRASSE"
        c.execute("UPDATE records SET payload=? WHERE id='a'", (json.dumps(r),))
    assert client.get("/api/pairs", params={"q": "café straße"}).json()["total"] == 1


def test_changed_entity_not_exported(client):
    payload = dict(
        kind="SAME",
        rationale="Before source change",
        revision=1,
        idempotency_key="historical-entity",
        context_version=client.get("/api/pairs/ab/impact").json()["context_version"],
    )
    assert client.post("/api/pairs/ab/decision", json=payload).status_code == 200
    with store.connect() as c:
        r = json.loads(
            c.execute("SELECT payload FROM records WHERE id='b'").fetchone()[0]
        )
        r.update(version="v2", name="Successor business")
        c.execute("UPDATE records SET payload=? WHERE id='b'", (json.dumps(r),))
    e = client.get("/api/entities").json()[0]
    assert e["needs_review"] and e["members"][1]["name"] == "Other Cafe"
    assert client.get("/api/export").json()["excluded_changed_entities"] == 1
    assert client.get("/api/export").json()["entities"] == []
    assert client.get("/api/pairs").json()["items"][0]["source_stale"]


def test_equal_model_scores_use_observed_similarity_tiebreak(client):
    with store.connect() as c:
        p = json.loads(
            c.execute("SELECT payload FROM pairs WHERE id='ab'").fetchone()[0]
        )
        p["baseline"] = 0.4
        c.execute("UPDATE pairs SET payload=? WHERE id='ab'", (json.dumps(p),))
        other = dict(p, id="zz", baseline=0.95)
        c.execute(
            "INSERT INTO pairs(id,payload) VALUES(?,?)", ("zz", json.dumps(other))
        )
    assert client.get("/api/pairs").json()["items"][0]["id"] == "zz"
