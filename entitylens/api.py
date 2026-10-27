import json, uuid, time, csv, io
from typing import Literal
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, JSONResponse
from entitylens.evidence import describe_pair
from pydantic import BaseModel, Field
from entitylens import store

app = FastAPI(title="EntityLens", version="0.1.0")
store.bootstrap()


class Decision(BaseModel):
    kind: str
    rationale: str = Field(min_length=1, max_length=2000)
    revision: int
    idempotency_key: str = Field(min_length=8, max_length=100)
    context_version: str = Field(min_length=64, max_length=64)


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
    q: str = Query("", max_length=200),
    state: str = "",
    order: Literal["score", "disagreement"] = "score",
):
    with store.connect() as c:
        c.execute("BEGIN")
        where = "WHERE (?='' OR json_extract(p.payload,'$.status')=?) AND (?='' OR instr(casefold(coalesce(json_extract(a.payload,'$.name'),'') || ' ' || coalesce(json_extract(b.payload,'$.name'),'') || ' ' || coalesce(json_extract(a.payload,'$.address'),'') || ' ' || coalesce(json_extract(b.payload,'$.address'),'') || ' ' || p.id),casefold(?))>0)"
        join = " FROM pairs p JOIN records a ON a.id=json_extract(p.payload,'$.left') JOIN records b ON b.id=json_extract(p.payload,'$.right') "
        params = (state, state, q, q)
        total = c.execute("SELECT count(*)" + join + where, params).fetchone()[0]
        ordering = (
            "json_extract(p.payload,'$.score') DESC,coalesce(json_extract(p.payload,'$.baseline'),0) DESC,p.id"
            if order == "score"
            else "CASE WHEN json_extract(p.payload,'$.model') IS NOT NULL THEN abs(json_extract(p.payload,'$.score')-coalesce(json_extract(p.payload,'$.baseline'),json_extract(p.payload,'$.score'))) ELSE 0 END DESC,"
            + "json_extract(p.payload,'$.score') DESC,p.id"
        )
        result = c.execute(
            "SELECT p.*,a.payload AS a,b.payload AS b"
            + join
            + where
            + " ORDER BY "
            + ordering
            + " LIMIT ? OFFSET ?",
            params + (limit, offset),
        )
        return dict(
            total=total,
            items=[
                dict(
                    **json.loads(r["payload"]),
                    revision=r["revision"],
                    source_stale=json.loads(r["payload"])["versions"]
                    != [json.loads(r["a"])["version"], json.loads(r["b"])["version"]],
                    a=json.loads(r["a"]),
                    b=json.loads(r["b"]),
                )
                for r in result
            ],
        )


def pair_payload(c, ident):
    row = c.execute("SELECT * FROM pairs WHERE id=?", (ident,)).fetchone()
    if not row:
        raise HTTPException(404, "Proposal not found")
    p = json.loads(row["payload"])
    records = [
        json.loads(
            c.execute("SELECT payload FROM records WHERE id=?", (p[k],)).fetchone()[0]
        )
        for k in ["left", "right"]
    ]
    return dict(
        **p,
        revision=row["revision"],
        a=records[0],
        b=records[1],
        source_stale=p["versions"] != [r["version"] for r in records],
        evidence=describe_pair(*records, p),
    )


@app.get("/api/pairs/{ident}")
def pair_detail(ident: str):
    with store.connect() as c:
        c.execute("BEGIN")
        return pair_payload(c, ident)


@app.post("/api/pairs/{ident}/decision")
def decision(ident: str, d: Decision):
    try:
        return store.decide(
            ident,
            d.kind,
            d.rationale,
            d.revision,
            d.idempotency_key,
            context_version=d.context_version,
        )
    except KeyError:
        raise HTTPException(404, "Proposal not found")
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/entities")
def entities():
    with store.connect() as c:
        c.execute("BEGIN")
        groups, rs = store.components(c)
        out = []
        for g in groups:
            if len(g) < 2:
                continue
            reviewed, changed = store.reviewed_members(c, g, rs)
            members = [reviewed[k] for k in sorted(g)]
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
            out.append(
                dict(
                    id="entity:" + min(g),
                    members=members,
                    fields=fields,
                    needs_review=bool(changed),
                    changed_records=changed,
                )
            )
        return out


@app.get("/api/history")
def history():
    with store.connect() as c:
        c.execute("BEGIN")
        output = []
        for row in c.execute(
            "SELECT d.*,p.payload AS pair_payload FROM decisions d JOIN pairs p ON p.id=d.pair_id ORDER BY d.created DESC,d.id LIMIT 100"
        ):
            d = dict(row)
            p = json.loads(d.pop("pair_payload"))
            reviewed = {
                r["record_id"]: json.loads(r["payload"])
                for r in c.execute(
                    "SELECT record_id,payload FROM decision_records WHERE decision_id=?",
                    (d["id"],),
                )
            }
            d["record_names"] = [
                reviewed[k].get("name", "Unnamed place")
                if k in reviewed
                else "Historical record unavailable"
                for k in [p["left"], p["right"]]
            ]
            d["record_versions"] = [
                reviewed[k]["version"] if k in reviewed else None
                for k in [p["left"], p["right"]]
            ]
            output.append(d)
        return output


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
        c.execute("BEGIN IMMEDIATE")
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
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT status FROM jobs WHERE id=?", (ident,)).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        if row["status"] == "cancelled":
            return {"status": "cancelled"}
        if row["status"] not in ("queued", "running"):
            raise HTTPException(409, "Only queued or running jobs can be cancelled")
        c.execute(
            "UPDATE jobs SET status='cancelled',lease=NULL WHERE id=? AND status IN ('queued','running')",
            (ident,),
        )
    return {"status": "cancelled"}


@app.post("/api/jobs/{ident}/retry")
def retry_job(ident: str):
    with store.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT status FROM jobs WHERE id=?", (ident,)).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        if row["status"] not in ("failed", "cancelled"):
            raise HTTPException(409, "Only failed or cancelled jobs can be retried")
        if c.execute(
            "SELECT 1 FROM jobs WHERE status IN ('queued','running')"
        ).fetchone():
            raise HTTPException(409, "Another matching run is active")
        c.execute(
            "UPDATE jobs SET status='queued',attempts=0,error=NULL WHERE id=? AND status IN ('failed','cancelled')",
            (ident,),
        )
    return {"status": "queued"}


def spreadsheet_value(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    text = "" if value is None else str(value)
    if text.startswith(("\t", "\r", "\n")) or text.lstrip().startswith(
        ("=", "+", "-", "@")
    ):
        return "'" + text
    return text


@app.get("/api/export")
def export(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    format: Literal["json", "csv"] = "json",
):
    snapshot = entities()
    safe = sorted((e for e in snapshot if not e["needs_review"]), key=lambda e: e["id"])
    page = safe[offset : offset + limit]
    excluded = sum(e["needs_review"] for e in snapshot)
    headers = {
        "Content-Disposition": f'attachment; filename="entitylens-entities.{format}"',
        "X-Export-Total": str(len(safe)),
        "X-Export-Excluded": str(excluded),
    }
    if format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(
            [
                "entity_id",
                "name",
                "address",
                "phone",
                "latitude",
                "longitude",
                "member_count",
                "source_record_ids",
            ]
        )
        for entity in page:
            values = [
                entity["id"],
                *[
                    entity["fields"][field]["value"]
                    for field in ["name", "address", "phone", "lat", "lon"]
                ],
                len(entity["members"]),
                " | ".join(r["id"] for r in entity["members"]),
            ]
            writer.writerow([spreadsheet_value(v) for v in values])
        return Response(
            stream.getvalue(), media_type="text/csv; charset=utf-8", headers=headers
        )
    return JSONResponse(
        dict(
            entities=page,
            excluded_changed_entities=excluded,
            total=len(safe),
            offset=offset,
            limit=limit,
            next_offset=offset + limit if offset + limit < len(safe) else None,
            format="json",
            generated_at=datetime.now(timezone.utc).isoformat(),
            policy="local analyst decisions; source provenance included",
        ),
        headers=headers,
    )


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
        c.execute("BEGIN")
        context = store.review_context(c, ident)
        context["evidence"] = pair_payload(c, ident)["evidence"]
        return context


if Path("web/dist").exists():
    app.mount("/", StaticFiles(directory="web/dist", html=True), name="workbench")
