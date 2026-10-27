import csv, io, json
import pytest
from entitylens import store
from entitylens.evidence import describe_pair


def decide(client, kind="SAME", key="enhancement-review"):
    preview = client.get("/api/pairs/ab/impact").json()
    return client.post(
        "/api/pairs/ab/decision",
        json=dict(
            kind=kind,
            rationale="Fixture source evidence",
            revision=1,
            idempotency_key=key,
            context_version=preview["context_version"],
        ),
    )


def test_preview_and_confirmation_share_safety_reasons(client):
    with store.connect() as c:
        b = json.loads(
            c.execute("SELECT payload FROM records WHERE id='b'").fetchone()[0]
        )
        b["address"] = "12 Main St Suite 2"
        c.execute("UPDATE records SET payload=? WHERE id='b'", (json.dumps(b),))
    preview = client.get("/api/pairs/ab/impact").json()
    assert preview["pair_id"] == "ab"
    assert preview["merge_blockers"][0]["code"] == "street_number"
    assert preview["evidence"]["distance_m"] == 0
    assert decide(client).status_code == 409
    assert decide(client, "DIFFERENT", "valid-separate").status_code == 200


def test_detail_and_address_search_are_independent_of_queue(client):
    detail = client.get("/api/pairs/ab").json()
    assert detail["a"]["name"] == "Cafe 100%"
    assert detail["evidence"]["model"] == "rule baseline"
    assert detail["evidence"]["score_disagreement"] is None
    assert client.get("/api/pairs/missing").status_code == 404
    assert client.get("/api/pairs", params={"q": "1 MAIN"}).json()["total"] == 1
    assert decide(client).status_code == 200
    assert client.get("/api/pairs?state=REVIEW").json()["total"] == 0
    assert client.get("/api/pairs/ab").json()["status"] == "SAME"


def test_disagreement_order_targets_discordant_model_scores(client):
    with store.connect() as c:
        p = json.loads(
            c.execute("SELECT payload FROM pairs WHERE id='ab'").fetchone()[0]
        )
        p.update(score=0.95, baseline=0.94, model="classifier")
        c.execute("UPDATE pairs SET payload=? WHERE id='ab'", (json.dumps(p),))
        other = dict(p, id="discordant", score=0.85, baseline=0.1)
        c.execute(
            "INSERT INTO pairs(id,payload) VALUES(?,?)",
            (other["id"], json.dumps(other)),
        )
    assert client.get("/api/pairs?order=score").json()["items"][0]["id"] == "ab"
    assert (
        client.get("/api/pairs?order=disagreement").json()["items"][0]["id"]
        == "discordant"
    )
    assert client.get("/api/pairs?order=invalid").status_code == 422
    assert client.get("/api/pairs", params={"q": "x" * 201}).status_code == 422


@pytest.mark.parametrize(
    "name", ["=2+2", " +SUM(A1:A2)", "@SUM(A1:A2)", "\t=2+2", "-2+3"]
)
def test_csv_neutralizes_untrusted_spreadsheet_formulas(client, name):
    with store.connect() as c:
        a = json.loads(
            c.execute("SELECT payload FROM records WHERE id='a'").fetchone()[0]
        )
        a["name"] = name
        c.execute("UPDATE records SET payload=? WHERE id='a'", (json.dumps(a),))
    assert decide(client).status_code == 200
    response = client.get("/api/export?format=csv")
    assert response.status_code == 200 and response.headers["content-type"].startswith(
        "text/csv"
    )
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]["name"] == "'" + name
    assert rows[0]["longitude"] == "-74.0"
    assert response.headers["content-disposition"].endswith('"entitylens-entities.csv"')


def test_export_is_bounded_and_preserves_json_provenance(client):
    assert decide(client).status_code == 200
    export = client.get("/api/export?format=json&limit=1").json()
    assert export["total"] == 1 and export["next_offset"] is None
    assert export["entities"][0]["fields"]["name"]["selected_from"] == "a"
    assert client.get("/api/export?offset=1").json()["entities"] == []
    assert client.get("/api/export?format=xml").status_code == 422
    assert client.get("/api/export?limit=501").status_code == 422
    with store.connect() as c:
        a = json.loads(
            c.execute("SELECT payload FROM records WHERE id='a'").fetchone()[0]
        )
        a["version"] = "v2"
        c.execute("UPDATE records SET payload=? WHERE id='a'", (json.dumps(a),))
    assert (
        list(csv.DictReader(io.StringIO(client.get("/api/export?format=csv").text)))
        == []
    )
    assert client.get("/api/export?format=csv").headers["x-export-excluded"] == "1"


def test_history_uses_immutable_reviewed_names(client):
    assert decide(client).status_code == 200
    with store.connect() as c:
        a = json.loads(
            c.execute("SELECT payload FROM records WHERE id='a'").fetchone()[0]
        )
        a.update(name="Successor", version="v2")
        c.execute("UPDATE records SET payload=? WHERE id='a'", (json.dumps(a),))
    h = client.get("/api/history").json()[0]
    assert h["record_names"] == ["Cafe 100%", "Other Cafe"]
    assert h["record_versions"] == ["v1", "v1"]


def test_missing_fields_never_produce_positive_evidence():
    a = dict(id="a", name="", address="", phone="", lat=None, lon=None)
    b = dict(a, id="b")
    evidence = describe_pair(a, b, dict(score=0.9, baseline=0.4))
    assert evidence["signals"] == [] and len(evidence["missing"]) == 4
    assert evidence["distance_m"] is None and evidence["score_disagreement"] is None


def test_csv_roundtrips_unicode_quotes_and_commas(client):
    name = 'Café "Rive, Gauche"'
    with store.connect() as c:
        a = json.loads(
            c.execute("SELECT payload FROM records WHERE id='a'").fetchone()[0]
        )
        a["name"] = name
        c.execute("UPDATE records SET payload=? WHERE id='a'", (json.dumps(a),))
    assert decide(client).status_code == 200
    rows = list(csv.DictReader(io.StringIO(client.get("/api/export?format=csv").text)))
    assert rows[0]["name"] == name


def test_export_next_page_metadata(client):
    assert decide(client).status_code == 200
    with store.connect() as c:
        for ident in ["c", "d"]:
            r = dict(
                id=ident,
                name="Second cafe",
                address="2 Main",
                source=ident,
                version="v1",
                lat=40.0,
                lon=-74.0,
                phone="",
            )
            c.execute("INSERT INTO records VALUES(?,?)", (ident, json.dumps(r)))
        p = dict(
            id="cd",
            left="c",
            right="d",
            versions=["v1", "v1"],
            status="REVIEW",
            features=[1] * 8,
            score=0.9,
            baseline=0.9,
        )
        c.execute("INSERT INTO pairs(id,payload) VALUES(?,?)", ("cd", json.dumps(p)))
    context = client.get("/api/pairs/cd/impact").json()["context_version"]
    assert (
        client.post(
            "/api/pairs/cd/decision",
            json=dict(
                kind="SAME",
                rationale="Second physical place",
                revision=1,
                idempotency_key="second-entity-key",
                context_version=context,
            ),
        ).status_code
        == 200
    )
    first = client.get("/api/export?limit=1").json()
    second = client.get("/api/export?limit=1&offset=1").json()
    assert first["total"] == 2 and first["next_offset"] == 1
    assert second["next_offset"] is None
    assert first["entities"][0]["id"] != second["entities"][0]["id"]
