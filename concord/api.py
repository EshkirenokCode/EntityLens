import json, uuid, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from concord import store

app = FastAPI(title="Concord", version="0.1.0")
store.bootstrap()


class Decision(BaseModel):
    kind: str
    rationale: str = Field(min_length=1, max_length=2000)
    revision: int
    idempotency_key: str = Field(min_length=8, max_length=100)


@app.get("/api/status")
def status():
    with store.connect() as c:
        return dict(
            records=c.execute("SELECT count(*) FROM records").fetchone()[0],
            pairs=c.execute("SELECT count(*) FROM pairs").fetchone()[0],
            decisions=c.execute(
                "SELECT count(*) FROM decisions WHERE undone=0"
            ).fetchone()[0],
            policy="review-only",
            data_quality=json.loads(Path("reports/data-quality.json").read_text())
            if Path("reports/data-quality.json").exists()
            else None,
        )


@app.get("/api/pairs")
def pairs(
    offset: int = Query(0, ge=0),
    limit: int = Query(40, ge=1, le=100),
    q: str = "",
    state: str = "",
):
    with store.connect() as c:
        rs = {r["id"]: r for r in store.rows(c, "records")}
        out = []
        for row in c.execute("SELECT * FROM pairs"):
            p = json.loads(row["payload"])
            if state and p["status"] != state:
                continue
            if (
                q
                and q.casefold()
                not in (rs[p["left"]]["name"] + " " + rs[p["right"]]["name"]).casefold()
            ):
                continue
            out.append(
                dict(**p, revision=row["revision"], a=rs[p["left"]], b=rs[p["right"]])
            )
        out.sort(key=lambda p: (-p["score"], p["id"]))
        return dict(total=len(out), items=out[offset : offset + limit])


@app.post("/api/pairs/{ident}/decision")
def decision(ident: str, d: Decision):
    try:
        return store.decide(ident, d.kind, d.rationale, d.revision, d.idempotency_key)
    except KeyError:
        raise HTTPException(404, "Proposal not found")
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/entities")
def entities():
    with store.connect() as c:
        groups, rs = store.components(c)
        out = []
        for g in groups:
            if len(g) < 2:
                continue
            members = [rs[k] for k in sorted(g)]
            fields = {}
            for field in ["name", "address", "lat", "lon", "phone"]:
                values = [
                    dict(record=r["id"], version=r["version"], value=r.get(field))
                    for r in members
                    if r.get(field) is not None and r.get(field) != ""
                ]
                fields[field] = dict(
                    value=values[0]["value"] if values else None,
                    selected_from=values[0]["record"] if values else None,
                    method="stable source order; analyst may inspect all values",
                    values=values,
                    conflict=len({str(v["value"]) for v in values}) > 1,
                )
            out.append(dict(id="entity:" + min(g), members=members, fields=fields))
        return out


@app.get("/api/history")
def history():
    with store.connect() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT * FROM decisions ORDER BY created DESC LIMIT 100"
            )
        ]


@app.post("/api/decisions/{ident}/undo")
def undo(ident: str):
    try:
        store.undo(ident)
        return {"status": "undone"}
    except KeyError:
        raise HTTPException(404, "Decision not found")
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/evaluation")
def evaluation():
    p = Path("reports/evaluation.json")
    return (
        json.loads(p.read_text())
        if p.exists()
        else dict(status="Training pending", gold_available=False)
    )


@app.get("/api/sources")
def sources():
    return [json.loads(p.read_text()) for p in Path("data/manifests").glob("*.json")]


@app.post("/api/jobs")
def job():
    with store.connect() as c:
        row = c.execute(
            "SELECT id FROM jobs WHERE status IN ('queued','running')"
        ).fetchone()
        if row:
            return dict(id=row[0])
        ident = str(uuid.uuid4())
        c.execute(
            "INSERT INTO jobs(id,status,created) VALUES(?,?,?)",
            (ident, "queued", time.time()),
        )
        return dict(id=ident)


@app.get("/api/jobs")
def jobs():
    with store.connect() as c:
        return [
            dict(r)
            for r in c.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 30")
        ]


@app.post("/api/jobs/{ident}/cancel")
def cancel_job(ident: str):
    with store.connect() as c:
        c.execute(
            "UPDATE jobs SET status='cancelled',lease=NULL WHERE id=? AND status IN ('queued','running')",
            (ident,),
        )
    return {"status": "cancelled"}


@app.post("/api/jobs/{ident}/retry")
def retry_job(ident: str):
    with store.connect() as c:
        c.execute(
            "UPDATE jobs SET status='queued',attempts=0,error=NULL WHERE id=? AND status IN ('failed','cancelled')",
            (ident,),
        )
    return {"status": "queued"}


@app.get("/api/export")
def export(limit: int = Query(100, ge=1, le=500)):
    return {
        "entities": entities()[:limit],
        "format": "json",
        "policy": "local analyst decisions; source provenance included",
    }


@app.get("/api/monitoring")
def monitoring():
    with store.connect() as c:
        ps = store.rows(c, "pairs")
        scores = [p["score"] for p in ps]
        bins = [sum(i / 10 <= s < (i + 1) / 10 for s in scores) for i in range(10)]
        bins[-1] += sum(s == 1 for s in scores)
        return dict(
            score_histogram=bins,
            candidate_count=len(ps),
            review_count=sum(p["status"] == "REVIEW" for p in ps),
            job_errors=c.execute(
                "SELECT count(*) FROM jobs WHERE error IS NOT NULL"
            ).fetchone()[0],
            quality_warning="Distribution changes are signals, not measured accuracy loss",
        )


@app.get("/api/pairs/{ident}/impact")
def impact(ident: str):
    with store.connect() as c:
        row = c.execute("SELECT payload FROM pairs WHERE id=?", (ident,)).fetchone()
        if not row:
            raise HTTPException(404, "Proposal not found")
        p = json.loads(row[0])
        groups, rs = store.components(c)
        affected = sorted(
            {k for g in groups if p["left"] in g or p["right"] in g for k in g}
        )
        return dict(
            members=[
                dict(
                    id=k,
                    name=rs[k]["name"],
                    address=rs[k]["address"],
                    version=rs[k]["version"],
                )
                for k in affected
            ],
            record_versions=p["versions"],
            policy="Full group checked for cannot-link and location conflicts on confirmation",
        )


if Path("web/dist").exists():
    app.mount("/", StaticFiles(directory="web/dist", html=True), name="workbench")
