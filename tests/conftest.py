import json
import pytest
from fastapi.testclient import TestClient
from entitylens import store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", str(tmp_path / "api.db"))
    monkeypatch.setattr(store, "bootstrap", store.init)
    from entitylens.api import app

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
