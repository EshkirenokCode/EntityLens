import React, { useState, useEffect, useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  Layers,
  GitMerge,
  Database,
  ChartNoAxesCombined,
  Search,
  ArrowRight,
  Check,
  X,
  HelpCircle,
  Undo2,
  MapPin,
  ChevronRight,
  Activity,
  RefreshCw,
} from "lucide-react";
import "./style.css";
type RecordRow = {
  id: string;
  name: string;
  address: string;
  source: string;
  lat: number | null;
  lon: number | null;
  phone: string;
  version: string;
};
type Pair = {
  id: string;
  a: RecordRow;
  b: RecordRow;
  features: number[];
  score: number;
  baseline: number;
  status: string;
  revision: number;
  source_stale: boolean;
};
async function api(path: string, body?: unknown) {
  const r = await fetch(
    "/api/" + path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  let d;
  try {
    d = await r.json();
  } catch {
    throw Error(`Service returned an invalid response (HTTP ${r.status}).`);
  }
  if (!r.ok)
    throw Error(
      Array.isArray(d.detail)
        ? d.detail
            .map((v: any) => `${v.loc?.slice(1).join(".")}: ${v.msg}`)
            .join("; ")
        : d.detail || `Request failed (HTTP ${r.status})`,
    );
  return d;
}
function hasCoordinates(
  r: RecordRow,
): r is RecordRow & { lat: number; lon: number } {
  return (
    typeof r.lat === "number" &&
    typeof r.lon === "number" &&
    Number.isFinite(r.lat) &&
    Number.isFinite(r.lon) &&
    Math.abs(r.lat) <= 90 &&
    Math.abs(r.lon) <= 180
  );
}
function pinStyle(a: RecordRow, b: RecordRow) {
  if (!hasCoordinates(a) || !hasCoordinates(b)) return undefined;
  const span = Math.max(
    Math.abs(a.lon - b.lon),
    Math.abs(a.lat - b.lat),
    0.001,
  );
  return {
    left: `${50 + ((a.lon - b.lon) / span) * 30}%`,
    top: `${50 - ((a.lat - b.lat) / span) * 30}%`,
  };
}
const fmt = (n: number) => new Intl.NumberFormat("en").format(n || 0);
function App() {
  const [page, setPage] = useState("Review"),
    [status, S] = useState<any>({}),
    [pairs, P] = useState<Pair[]>([]),
    [selected, I] = useState(0),
    [q, Q] = useState(""),
    [search, DS] = useState(""),
    [queueState, QS] = useState("REVIEW"),
    [previewEpoch, PE] = useState(0),
    [previewError, PRE] = useState(""),
    [total, T] = useState(0),
    [offset, O] = useState(0),
    [error, E] = useState(""),
    [busy, B] = useState(false),
    [loading, L] = useState(true),
    [note, N] = useState(""),
    [toast, V] = useState(""),
    [entities, EN] = useState<any[]>([]),
    [history, H] = useState<any[]>([]),
    [evaluation, EV] = useState<any>({}),
    [sources, SO] = useState<any[]>([]),
    [jobs, J] = useState<any[]>([]),
    [impact, IM] = useState<any>(null);
  useEffect(() => {
    const t = setTimeout(() => DS(q), 200);
    return () => clearTimeout(t);
  }, [q]);
  useEffect(() => {
    if (page !== "Sources & Runs") return;
    let current = true;
    const t = setInterval(
      () =>
        api("jobs")
          .then((v) => {
            if (current) J(v);
          })
          .catch((e) => {
            if (current) E(String(e));
          }),
      2000,
    );
    return () => {
      current = false;
      clearInterval(t);
    };
  }, [page]);
  const requestId = useRef(0);
  const pendingDecision = useRef<{ signature: string; key: string } | null>(
    null,
  );
  const refresh = useCallback(async () => {
    const request = ++requestId.current;
    L(true);
    try {
      const [s, p, e, h, v, src, j] = await Promise.all([
        api("status"),
        api(
          `pairs?q=${encodeURIComponent(search)}&offset=${offset}&state=${queueState}`,
        ),
        api("entities"),
        api("history"),
        api("evaluation"),
        api("sources"),
        api("jobs"),
      ]);
      if (request !== requestId.current) return;
      if (offset > 0 && p.total <= offset) {
        O(Math.max(0, Math.floor((p.total - 1) / 40) * 40));
        return;
      }
      S(s);
      P(p.items);
      I((i) => Math.min(Math.max(i, 0), Math.max(0, p.items.length - 1)));
      T(p.total);
      EN(e);
      H(h);
      EV(v);
      SO(src);
      J(j);
      PE((i) => i + 1);
      E("");
    } catch (e) {
      if (request === requestId.current) E(String(e));
    } finally {
      if (request === requestId.current) L(false);
    }
  }, [search, offset, queueState]);
  useEffect(() => {
    refresh();
  }, [refresh]);
  const p = pairs[selected];
  useEffect(() => {
    N("");
  }, [p?.id]);
  useEffect(() => {
    let current = true;
    IM(null);
    PRE("");
    if (p)
      api(`pairs/${p.id}/impact`)
        .then((v) => {
          if (current) IM(v);
        })
        .catch((e) => {
          if (current) PRE(String(e));
        });
    return () => {
      current = false;
    };
  }, [p?.id, p?.revision, previewEpoch]);
  async function decide(kind: string) {
    if (
      !p ||
      busy ||
      loading ||
      !impact?.context_version ||
      p.source_stale ||
      p.status !== "REVIEW"
    )
      return;
    if (!note.trim()) {
      E("Add an evidence note before recording your decision.");
      return;
    }
    B(true);
    try {
      const signature = JSON.stringify([
        p.id,
        p.revision,
        kind,
        note,
        impact.context_version,
      ]);
      if (pendingDecision.current?.signature !== signature)
        pendingDecision.current = { signature, key: crypto.randomUUID() };
      await api(`pairs/${p.id}/decision`, {
        kind,
        rationale: note,
        revision: p.revision,
        idempotency_key: pendingDecision.current.key,
        context_version: impact.context_version,
      });
      pendingDecision.current = null;
      V("Decision recorded. Source records preserved.");
      N("");
      await refresh();
    } catch (e) {
      E(String(e));
    } finally {
      B(false);
    }
  }
  useEffect(() => {
    function key(e: KeyboardEvent) {
      if (busy || loading || page !== "Review") return;
      if (
        ["INPUT", "TEXTAREA", "SELECT"].includes(
          (e.target as HTMLElement).tagName,
        )
      )
        return;
      if (e.key === "j" && pairs.length)
        I((i) => Math.min(i + 1, pairs.length - 1));
      if (e.key === "k") I((i) => Math.max(i - 1, 0));
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [pairs, busy, loading, page]);
  return (
    <div className="app">
      <aside className="sidebar">
        <a className="brand" href="/">
          <div className="brandmark">
            <Layers size={22} />
          </div>
          concord<span>WORKBENCH</span>
        </a>
        <div className="workspace">
          <span className="avatar">NY</span>
          <div>
            Lower Manhattan<small>Place resolution workspace</small>
          </div>
        </div>
        <p className="navlabel">WORKSPACE</p>
        <nav>
          {[
            ["Review", GitMerge],
            ["Sources & Runs", Database],
            ["Entities", Layers],
            ["Evaluation", ChartNoAxesCombined],
          ].map(([name, Icon]: any) => (
            <button
              disabled={busy}
              aria-label={name}
              aria-current={page === name ? "page" : undefined}
              className={page === name ? "active" : ""}
              key={name}
              onClick={() => setPage(name)}
            >
              <Icon size={18} />
              {name}
              {name === "Review" && <b>{fmt(total)}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebarbottom">
          <span className="dot" /> Local workspace
          <small>Review-only decision policy</small>
          <div className="profile">
            <span className="avatar">IG</span>
            <div>
              Ilia Gulevskii<small>Workspace owner</small>
            </div>
          </div>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <strong>{page}</strong>
          </div>
          <span className="local">
            <span className="dot" /> LOCAL ENVIRONMENT
          </span>
        </header>
        <div className="content">
          <div className="title">
            <div>
              <div className="eyebrow">ENTITY RESOLUTION / NYC</div>
              <h1>{page === "Review" ? "Resolve places" : page}</h1>
              <p>
                {page === "Review"
                  ? "Compare independent records and record a traceable decision."
                  : page === "Evaluation"
                    ? "Measured results, reproducible runs, explicit limitations."
                    : page === "Entities"
                      ? "Confirmed places with complete source lineage."
                      : "Independent catalogs. Immutable snapshots. Traceable runs."}
              </p>
            </div>
            <button className="secondary" onClick={refresh}>
              <RefreshCw size={15} />
              Refresh
            </button>
          </div>
          {error && (
            <div role="alert" className="alert">
              {error}
              <button
                onClick={() => {
                  E("");
                  refresh();
                }}
              >
                Retry
              </button>
            </div>
          )}
          {toast && (
            <div className="notice" onClick={() => V("")}>
              {toast} ×
            </div>
          )}
          <div className="stats">
            {[
              [
                "Source records",
                fmt(status.records),
                "Across 2 independent catalogs",
              ],
              [
                "Candidate pairs",
                fmt(status.pairs),
                "Spatial + lexical retrieval",
              ],
              [
                "Reviewed pairs",
                fmt(status.decisions),
                "Evidence-backed decisions",
              ],
              ["Decision policy", "Review only", "Independent gold required"],
            ].map(([a, b, c]) => (
              <div key={a}>
                <small>{a}</small>
                <strong>{b}</strong>
                <span>{c}</span>
              </div>
            ))}
          </div>
          {page === "Review" && (
            <>
              <div className="sectiontitle">
                <h2>
                  Review queue <span>{fmt(total)} pairs</span>
                </h2>
                <span className="muted">Navigate with J / K</span>
              </div>
              <div className="workbench">
                <section className="queue">
                  <div className="search">
                    <Search size={16} />
                    <input
                      disabled={busy}
                      aria-label="Search places"
                      placeholder="Search places…"
                      value={q}
                      onChange={(e) => {
                        Q(e.target.value);
                        O(0);
                        I(0);
                      }}
                    />
                  </div>
                  <div className="queuefilters">
                    <label htmlFor="queue-status">Show</label>
                    <select
                      id="queue-status"
                      aria-label="Review status"
                      disabled={busy}
                      value={queueState}
                      onChange={(e) => {
                        QS(e.target.value);
                        O(0);
                        I(0);
                      }}
                    >
                      <option value="REVIEW">Needs review</option>
                      <option value="SAME">Same place</option>
                      <option value="DIFFERENT">Different places</option>
                      <option value="UNCERTAIN">Unsure</option>
                      <option value="">All pairs</option>
                    </select>
                  </div>
                  <div className="queuelabel">
                    CANDIDATE PAIRS <span>SCORE ↓</span>
                  </div>
                  {error && pairs.length === 0 ? (
                    <div className="empty">
                      Data unavailable.
                      <small>Check the local service and retry.</small>
                    </div>
                  ) : loading ? (
                    <div className="empty">Loading records…</div>
                  ) : pairs.length === 0 ? (
                    <div className="empty">
                      No matching pairs.
                      <small>
                        {status.records
                          ? "Try another search or review-status filter."
                          : "Import and process sources to begin."}
                      </small>
                    </div>
                  ) : (
                    pairs.map((x, i) => (
                      <button
                        key={x.id}
                        disabled={busy}
                        aria-pressed={i === selected}
                        className={"pair " + (i === selected ? "chosen" : "")}
                        onClick={() => {
                          I(i);
                          N("");
                          E("");
                        }}
                      >
                        <div>
                          <strong>{x.a.name}</strong>
                          <span>{x.b.name}</span>
                          <small>
                            <MapPin size={11} />
                            {x.a.address}
                          </small>
                        </div>
                        <b>
                          {x.score.toFixed(3)}
                          <small>model score</small>
                        </b>
                        <em
                          className={x.status === "REVIEW" ? "tag" : "tag done"}
                        >
                          {x.status === "REVIEW" ? "Needs review" : x.status}
                        </em>
                      </button>
                    ))
                  )}
                  <div className="pagination">
                    <button
                      disabled={busy || loading || offset === 0}
                      onClick={() => {
                        O(Math.max(0, offset - 40));
                        I(0);
                      }}
                    >
                      Previous
                    </button>
                    <span>
                      {total ? offset + 1 : 0}–{Math.min(offset + 40, total)}
                    </span>
                    <button
                      disabled={busy || loading || offset + 40 >= total}
                      onClick={() => {
                        O(offset + 40);
                        I(0);
                      }}
                    >
                      Next
                    </button>
                  </div>
                </section>
                <section className="comparison">
                  {p ? (
                    <>
                      <div className="comparehead">
                        <span className="tag">
                          {p.status === "REVIEW" ? "Needs review" : p.status}
                        </span>
                        <span className="muted">Pair {p.id.slice(0, 8)}</span>
                      </div>
                      {p.source_stale && (
                        <div role="alert" className="alert">
                          Source records changed. Run matching again before
                          making a decision.
                        </div>
                      )}
                      <h2>Same place, different records?</h2>
                      <p className="muted">
                        Confirm the physical location, including branch and
                        address.
                      </p>
                      <div className="recordgrid">
                        {[p.a, p.b].map((r, i) => (
                          <article key={r.id}>
                            <div className="sourcebadge">
                              <span>{i ? "B" : "A"}</span>
                              {r.source === "nyc"
                                ? "NYC DOHMH"
                                : "Overture Places"}
                            </div>
                            <h3>{r.name}</h3>
                            {[
                              ["Address", r.address],
                              ["Business phone", r.phone || "Not provided"],
                              [
                                "Coordinates",
                                hasCoordinates(r)
                                  ? `${r.lat.toFixed(5)}, ${r.lon.toFixed(5)}`
                                  : "Not provided",
                              ],
                              ["Record version", r.version],
                            ].map(([a, b]) => (
                              <div className="field" key={a}>
                                <label>{a}</label>
                                <p>{b}</p>
                              </div>
                            ))}
                          </article>
                        ))}
                      </div>
                      <div className="evidence">
                        <div className="sectiontitle">
                          <h3>Observed evidence</h3>
                          <span className="muted">
                            Shared feature pipeline · v1
                          </span>
                        </div>
                        {[
                          ["Name similarity", p.features[0]],
                          ["Address similarity", p.features[2]],
                          ["Spatial proximity", p.features[4]],
                        ].map(([a, b]) => (
                          <div className="feature" key={String(a)}>
                            <span>{a}</span>
                            <div>
                              <i style={{ width: `${Number(b) * 100}%` }} />
                            </div>
                            <b>{(Number(b) * 100).toFixed(0)}%</b>
                          </div>
                        ))}
                        <div className="hint">
                          <HelpCircle size={15} />
                          Similarity is a model score, not a calibrated
                          probability. Shared brand or phone does not prove
                          branch identity.
                        </div>
                      </div>
                      <div className="reviewaction">
                        <label htmlFor="evidence-note">Decision evidence</label>
                        <textarea
                          id="evidence-note"
                          disabled={busy}
                          maxLength={2000}
                          placeholder="What supports your decision? Cite the address, branch or independent evidence…"
                          value={note}
                          onChange={(e) => N(e.target.value)}
                        />
                        {previewError && (
                          <div role="alert" className="alert">
                            Group preview unavailable: {previewError}
                            <button onClick={() => PE((i) => i + 1)}>
                              Retry preview
                            </button>
                          </div>
                        )}
                        <details className="impactpreview">
                          <summary>
                            Group impact ·{" "}
                            {impact ? impact.members.length : "…"} source
                            records
                          </summary>
                          {impact?.members.map((r: any) => (
                            <p key={r.id}>
                              {r.name} · {r.address}
                              <small>{r.id}</small>
                            </p>
                          ))}
                        </details>
                        <div className="impact">
                          <GitMerge size={14} />
                          Same place joins the full connected group after
                          cannot-link checks. Sources remain intact.
                        </div>
                        <div className="actions">
                          <button
                            disabled={
                              busy ||
                              loading ||
                              !impact?.context_version ||
                              p.source_stale ||
                              p.status !== "REVIEW"
                            }
                            className="primary"
                            onClick={() => decide("SAME")}
                          >
                            <Check size={16} />
                            Same place
                          </button>
                          <button
                            disabled={
                              busy ||
                              loading ||
                              !impact?.context_version ||
                              p.source_stale ||
                              p.status !== "REVIEW"
                            }
                            className="secondary"
                            onClick={() => decide("DIFFERENT")}
                          >
                            <X size={16} />
                            Different places
                          </button>
                          <button
                            disabled={
                              busy ||
                              loading ||
                              !impact?.context_version ||
                              p.source_stale ||
                              p.status !== "REVIEW"
                            }
                            className="secondary"
                            onClick={() => decide("UNCERTAIN")}
                          >
                            <HelpCircle size={16} />
                            Unsure
                          </button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="empty">
                      Select a pair to inspect source evidence.
                    </div>
                  )}
                </section>
                <aside className="context">
                  <h3>Location context</h3>
                  <div className="map">
                    <div className="mapgrid" />
                    {p && hasCoordinates(p.a) && hasCoordinates(p.b) && (
                      <>
                        <i className="pin pinA" style={pinStyle(p.a, p.b)}>
                          A
                        </i>
                        <i className="pin pinB" style={pinStyle(p.b, p.a)}>
                          B
                        </i>
                      </>
                    )}
                    <span className="mapcaption">RELATIVE COORDINATES</span>
                  </div>
                  <p className="mapnote">
                    Coordinate schematic · no external tiles
                    <small>Use source coordinates for exact location.</small>
                  </p>
                  <hr />
                  <h3>Resolution checklist</h3>
                  <ul>
                    <li>Same physical address?</li>
                    <li>Separate branches nearby?</li>
                    <li>Renaming or relocation?</li>
                    <li>Enough independent evidence?</li>
                  </ul>
                  <div className="callout">
                    <Activity size={18} />
                    <strong>Insufficient evidence?</strong>
                    <p>
                      Choose Unsure when the sources cannot establish identity.
                    </p>
                  </div>
                  <h3>Provenance</h3>
                  <p className="muted">
                    Immutable source versions are checked on every confirmation.
                    Conflicting group constraints block a merge.
                  </p>
                </aside>
              </div>
            </>
          )}
          {page === "Sources & Runs" && (
            <>
              <div className="cards">
                {sources.map((s) => (
                  <article className="panel" key={s.source}>
                    <div className="sourcebadge">
                      <Database size={18} />
                      {s.source === "nyc" ? "NYC DOHMH" : "Overture Places"}
                    </div>
                    <h2>Immutable source snapshot</h2>
                    <p className="muted">
                      {s.source === "nyc"
                        ? "Restaurant inspection catalog, deduplicated by CAMIS."
                        : "Published place records filtered to food establishments."}
                    </p>
                    <dl>
                      <dt>Retrieved</dt>
                      <dd>{s.retrieved_at}</dd>
                      <dt>Payload size</dt>
                      <dd>{(s.bytes / 1e6).toFixed(2)} MB</dd>
                      <dt>SHA-256</dt>
                      <dd className="hash">{s.sha256}</dd>
                    </dl>
                    <span className="tag done">Snapshot verified</span>
                  </article>
                ))}
              </div>
              <div className="panel">
                <h2>Matching runs</h2>
                <p className="muted">
                  A durable worker processes queued runs. Restarting the API
                  preserves state.
                </p>
                <button
                  className="primary"
                  onClick={async () => {
                    try {
                      await api("jobs", {});
                      await refresh();
                    } catch (e) {
                      E(String(e));
                    }
                  }}
                >
                  Queue matching run <ArrowRight size={15} />
                </button>
                {jobs.map((j) => (
                  <div className="history" key={j.id}>
                    <strong>{j.status}</strong>
                    <span>
                      {j.id.slice(0, 8)} · attempt {j.attempts}
                    </span>
                    <span>{j.error}</span>
                    {["queued", "running"].includes(j.status) && (
                      <button
                        className="secondary"
                        onClick={async () => {
                          try {
                            await api(`jobs/${j.id}/cancel`, {});
                            await refresh();
                          } catch (e) {
                            E(String(e));
                          }
                        }}
                      >
                        Cancel
                      </button>
                    )}
                    {["failed", "cancelled"].includes(j.status) && (
                      <button
                        className="secondary"
                        onClick={async () => {
                          try {
                            await api(`jobs/${j.id}/retry`, {});
                            await refresh();
                          } catch (e) {
                            E(String(e));
                          }
                        }}
                      >
                        Retry
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
          {page === "Entities" && (
            <>
              <div className="cards">
                {entities.length === 0 && (
                  <div className="panel empty">
                    No confirmed entities yet. Review a pair to create one.
                  </div>
                )}
                {entities.map((e) => (
                  <article className="panel" key={e.id}>
                    <span className="tag done">
                      {e.members.length} source records
                    </span>
                    {e.needs_review && (
                      <div role="alert" className="alert">
                        Source changed since confirmation. Showing reviewed
                        values; excluded from export. Undo the affected link and
                        run matching before confirming again.
                      </div>
                    )}
                    <h2>{e.fields.name.value}</h2>
                    <p>{e.fields.address.value}</p>
                    {Object.entries(e.fields).map(([k, f]: any) => (
                      <details key={k}>
                        <summary>
                          {k}{" "}
                          {f.conflict && (
                            <span className="tag">Source values differ</span>
                          )}
                        </summary>
                        {f.values.map((v: any) => (
                          <p key={v.record}>
                            {String(v.value)}
                            <small className="muted"> · {v.record}</small>
                          </p>
                        ))}
                      </details>
                    ))}
                  </article>
                ))}
              </div>
              <div className="panel">
                <h2>Decision history</h2>
                {history.length === 0 && (
                  <p className="muted">Recorded decisions will appear here.</p>
                )}
                {history.map((h) => (
                  <div className="history" key={h.id}>
                    <strong>{h.kind}</strong>
                    <span>{h.rationale}</span>
                    <button
                      className="secondary"
                      disabled={!!h.undone}
                      onClick={async () => {
                        try {
                          await api(`decisions/${h.id}/undo`, {});
                          await refresh();
                        } catch (e) {
                          E(String(e));
                        }
                      }}
                    >
                      <Undo2 size={14} />
                      {h.undone ? "Undone" : "Undo"}
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
          {page === "Evaluation" && (
            <>
              <div className="notice">
                {evaluation.label_provenance ||
                  "No independent human gold available."}{" "}
                · Automatic linking disabled.
              </div>
              <div className="panel">
                <div className="sectiontitle">
                  <h2>Model comparison</h2>
                  <span className="tag">
                    {evaluation.status || "Provisional evaluation"}
                  </span>
                </div>
                {evaluation.models ? (
                  <table>
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1</th>
                        <th>PR-AUC</th>
                        <th>Pairs</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(evaluation.models).map(([k, m]: any) => (
                        <tr key={k}>
                          <td>{k}</td>
                          <td>{m.precision.toFixed(3)}</td>
                          <td>{m.recall.toFixed(3)}</td>
                          <td>{m.f1.toFixed(3)}</td>
                          <td>{m.pr_auc.toFixed(3)}</td>
                          <td>{m.n}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p>Training results will appear after a reproducible run.</p>
                )}
                <h3>What these results establish</h3>
                <p className="muted">
                  Silver labels measure agreement with documented heuristics.
                  They do not establish accuracy on independently reviewed
                  places. Full retrieval recall, cluster accuracy and production
                  precision remain unproven.
                </p>
                <details>
                  <summary>Reproducibility manifest</summary>
                  <pre>{JSON.stringify(evaluation, null, 2)}</pre>
                </details>
              </div>
            </>
          )}
          <footer>
            Concord <span>Entity resolution workspace</span>
            <span>NYC DOHMH · Overture Maps Foundation</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
