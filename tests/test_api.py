import json, sqlite3
import pytest
from fastapi.testclient import TestClient
from concord import store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", str(tmp_path / "api.db"))
    monkeypatch.setattr(store, "bootstrap", store.init)
    from concord.api import app

    store.init()
    with store.connect() as c:
        for ident, name in [("a", "Cafe 100%"), ("b", "Other Cafe")]:
            r = dict(
                id=ident,
                name=name,
                address="1 Main",
                version="v1",
                lat=40.0,
                lon=-74.0,
                phone="",
                source=ident,
            )
            c.execute("INSERT INTO records VALUES(?,?)", (ident, json.dumps(r)))
        c.execute(
            "INSERT INTO pairs(id,payload) VALUES(?,?)",
            (
                "ab",
                json.dumps(
                    dict(
                        id="ab",
                        left="a",
                        right="b",
                        score=0.91,
                        status="REVIEW",
                        versions=["v1", "v1"],
                    )
                ),
            ),
        )
    return TestClient(app)


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
