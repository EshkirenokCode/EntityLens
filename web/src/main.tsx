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
  RefreshCw,
  Download,
  ExternalLink,
  ArrowLeft,
  Inbox,
} from "lucide-react";
import "./style.css";
import { PairAssessment, type GroupImpact } from "./components/PairAssessment";
import {
  RecordComparison,
  type SourceRecord as RecordRow,
} from "./components/RecordComparison";
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
  model?: string;
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
    [mobileInspect, MI] = useState(false),
    [status, S] = useState<any>({}),
    [pairs, P] = useState<Pair[]>([]),
    [selected, I] = useState(0),
    [q, Q] = useState(""),
    [search, DS] = useState(""),
    [queueState, QS] = useState("REVIEW"),
    [queueOrder, QO] = useState("score"),
    [opened, OP] = useState<Pair | null>(null),
    [opening, OPENING] = useState(false),
    [exporting, EX] = useState(false),
    [previewEpoch, PE] = useState(0),
    [previewError, PRE] = useState(""),
    [total, T] = useState(0),
    [offset, O] = useState(0),
    [error, E] = useState(""),
    [busy, B] = useState(false),
    [loading, L] = useState(true),
    [note, N] = useState(""),
    [noteError, NE] = useState(false),
    [toast, V] = useState(""),
    [entities, EN] = useState<any[]>([]),
    [history, H] = useState<any[]>([]),
    [evaluation, EV] = useState<any>({}),
    [sources, SO] = useState<any[]>([]),
    [jobs, J] = useState<any[]>([]),
    [impact, IM] = useState<GroupImpact | null>(null);
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
  const pairRequest = useRef(0);
  const openPair = useCallback(async (ident: string) => {
    const request = ++pairRequest.current;
    OPENING(true);
    setPage("Review");
    try {
      const item = await api(`pairs/${encodeURIComponent(ident)}`);
      if (request !== pairRequest.current) return;
      OP(item);
      MI(true);
      E("");
      window.history.replaceState(
        null,
        "",
        `#pair=${encodeURIComponent(ident)}`,
      );
    } catch (e) {
      if (request === pairRequest.current) E(String(e));
    } finally {
      if (request === pairRequest.current) OPENING(false);
    }
  }, []);
  const leaveOpened = () => {
    ++pairRequest.current;
    OP(null);
    MI(false);
    OPENING(false);
    window.history.replaceState(
      null,
      "",
      window.location.pathname + window.location.search,
    );
  };
  useEffect(() => {
    const read = () => {
      const ident = new URLSearchParams(window.location.hash.slice(1)).get(
        "pair",
      );
      if (ident) openPair(ident);
      else {
        ++pairRequest.current;
        OP(null);
        OPENING(false);
      }
    };
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, [openPair]);
  async function downloadEntities(format: "json" | "csv") {
    EX(true);
    try {
      const r = await fetch(`/api/export?format=${format}&limit=500`);
      if (!r.ok) throw Error(`Export failed (HTTP ${r.status})`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `entitylens-entities.${format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      V("Export downloaded. Changed entities are excluded.");
    } catch (e) {
      E(String(e));
    } finally {
      EX(false);
    }
  }
  const comparisonScroll = useRef<HTMLDivElement>(null);
  const queueList = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);
  const pendingDecision = useRef<{ signature: string; key: string } | null>(
    null,
  );
  const refresh = useCallback(async () => {
    const request = ++requestId.current;
    L(true);
    try {
      const [s, p, e, h, v, src, j, detail] = await Promise.all([
        api("status"),
        api(
          `pairs?q=${encodeURIComponent(search)}&offset=${offset}&state=${queueState}&order=${queueOrder}`,
        ),
        api("entities"),
        api("history"),
        api("evaluation"),
        api("sources"),
        api("jobs"),
        opened?.id ? api(`pairs/${opened.id}`) : Promise.resolve(null),
      ]);
      if (request !== requestId.current) return;
      if (offset > 0 && p.total <= offset) {
        O(Math.max(0, Math.floor((p.total - 1) / 40) * 40));
        return;
      }
      if (opened?.id && detail) OP(detail);
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
  }, [search, offset, queueState, queueOrder, opened?.id]);
  useEffect(() => {
    refresh();
  }, [refresh]);
  const p = opened || pairs[selected];
  useEffect(() => {
    N("");
    NE(false);
    if (comparisonScroll.current) comparisonScroll.current.scrollTop = 0;
  }, [p?.id]);
  useEffect(() => {
    queueList.current
      ?.querySelector<HTMLElement>('[aria-pressed="true"]')
      ?.scrollIntoView({ block: "nearest" });
  }, [selected, pairs, opened]);
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
      opening ||
      loading ||
      !impact?.context_version ||
      impact.pair_id !== p.id ||
      p.source_stale ||
      p.status !== "REVIEW"
    )
      return;
    if (kind === "SAME" && impact.merge_blockers?.length) {
      E(impact.merge_blockers[0].message);
      return;
    }
    if (!note.trim()) {
      NE(true);
      document.getElementById("evidence-note")?.focus();
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
      if (busy || opening || loading || page !== "Review" || opened) return;
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
  }, [pairs, busy, opening, opened, loading, page]);
  return (
    <div className={`app ${page === "Review" ? "reviewpage" : ""}`}>
      <aside className="sidebar">
        <a className="brand" href="/">
          <div className="brandmark">
            <Layers size={22} />
          </div>
          EntityLens<span>WORKBENCH</span>
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
            ["Review", Inbox],
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
              <span>{name === "Review" ? "Review queue" : name}</span>
            </button>
          ))}
        </nav>
        <div className="datasetnav">
          <p className="navlabel">CONNECTED SOURCES</p>
          <div>
            <span className="sourceinitial">N</span>NYC DOHMH
          </div>
          <div>
            <span className="sourceinitial">O</span>Overture Places
          </div>
          <small>{fmt(status.records)} records · Lower Manhattan</small>
        </div>
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
            Lower Manhattan <ChevronRight size={13} />
            <strong>{page}</strong>
          </div>
          <span className="local">
            <span className="dot" /> REVIEW ONLY
          </span>
        </header>
        <div className="content">
          <div className="title">
            <div>
              <h1>{page === "Review" ? "Review queue" : page}</h1>
              <p>
                {page === "Review"
                  ? "Decide which records belong to the same physical place."
                  : page === "Evaluation"
                    ? "Measured results, reproducible runs, explicit limitations."
                    : page === "Entities"
                      ? "Confirmed places with complete source lineage."
                      : "Independent catalogs. Immutable snapshots. Traceable runs."}
              </p>
            </div>
            <button
              className="secondary"
              aria-label="Refresh"
              onClick={refresh}
            >
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
          {page !== "Review" && (
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
          )}
          {page === "Review" && (
            <>
              <div className={`workbench ${mobileInspect ? "inspecting" : ""}`}>
                <section className="queue" aria-label="Candidate queue">
                  <div className="queueheading">
                    <h2>
                      Candidates <span>{fmt(total)}</span>
                    </h2>
                    <span className="keyhint">
                      <kbd>J</kbd>
                      <kbd>K</kbd>
                    </span>
                  </div>
                  <div className="queuetools">
                    <div className="search">
                      <Search size={16} />
                      <input
                        disabled={busy}
                        aria-label="Search places"
                        maxLength={200}
                        placeholder="Name, address or pair ID…"
                        value={q}
                        onChange={(e) => {
                          leaveOpened();
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
                          leaveOpened();
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
                    <div className="queuefilters">
                      <label htmlFor="queue-order">Order</label>
                      <select
                        id="queue-order"
                        aria-label="Queue order"
                        disabled={busy || opening}
                        value={queueOrder}
                        onChange={(e) => {
                          leaveOpened();
                          QO(e.target.value);
                          O(0);
                          I(0);
                        }}
                      >
                        <option value="score">Highest score</option>
                        <option value="disagreement">
                          Model / rule disagreement
                        </option>
                      </select>
                    </div>
                  </div>
                  <div className="queuelabel">
                    CANDIDATE PAIRS{" "}
                    <span>
                      {queueOrder === "score" ? "SCORE ↓" : "DISAGREEMENT ↓"}
                    </span>
                  </div>
                  <div className="pairlist" aria-busy={loading} ref={queueList}>
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
                          aria-pressed={!opened && i === selected}
                          className={
                            "pair " +
                            (!opened && i === selected ? "chosen" : "")
                          }
                          onClick={() => {
                            leaveOpened();
                            I(i);
                            MI(true);
                            N("");
                            E("");
                          }}
                        >
                          <div>
                            <strong title={x.a.name}>{x.a.name}</strong>
                            <span title={x.b.name}>{x.b.name}</span>
                            <small>
                              <MapPin size={11} />
                              {x.a.address}
                            </small>
                          </div>
                          <b>
                            {x.score.toFixed(3)}
                            <small>
                              {x.model ? "model score" : "rule score"}
                            </small>
                          </b>
                          {x.status !== "REVIEW" && (
                            <em
                              className={
                                x.status === "REVIEW" ? "tag" : "tag done"
                              }
                            >
                              {x.status === "REVIEW"
                                ? "Needs review"
                                : x.status}
                            </em>
                          )}
                        </button>
                      ))
                    )}
                  </div>
                  <div className="pagination">
                    <button
                      disabled={busy || loading || offset === 0}
                      onClick={() => {
                        leaveOpened();
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
                        leaveOpened();
                        O(offset + 40);
                        I(0);
                      }}
                    >
                      Next
                    </button>
                  </div>
                </section>
                <section className="comparison" aria-label="Selected pair">
                  <div className="comparisonbody" ref={comparisonScroll}>
                    <button className="mobileback" onClick={() => MI(false)}>
                      <ArrowLeft size={15} />
                      Back to candidates
                    </button>
                    {opened && (
                      <div className="openedpair">
                        Opened directly · {opened.id.slice(0, 8)}
                        <button onClick={leaveOpened} disabled={busy}>
                          Return to queue
                        </button>
                      </div>
                    )}
                    {opening && (
                      <div role="status" className="notice">
                        Opening pair…
                      </div>
                    )}
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
                        <h2>{p.a.name}</h2>
                        <p className="muted">
                          Compare source fields, then record your decision.
                        </p>
                        <RecordComparison a={p.a} b={p.b} />
                        {impact?.evidence && (
                          <PairAssessment
                            evidence={impact.evidence}
                            blockers={impact.merge_blockers}
                            model={p.model}
                            score={p.score}
                            baseline={p.baseline}
                          />
                        )}
                        <details className="evidence">
                          <summary>
                            Numeric features · proposal snapshot
                          </summary>
                          <div className="sectiontitle">
                            <h3>Pair feature values</h3>
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
                        </details>
                        <div className="reviewaction">
                          <div className="decisionheading">
                            <label htmlFor="evidence-note">Your decision</label>
                            <span className="muted">
                              Evidence note required
                            </span>
                          </div>
                          <textarea
                            id="evidence-note"
                            disabled={busy}
                            maxLength={2000}
                            aria-label="Decision evidence"
                            aria-required="true"
                            aria-invalid={noteError}
                            aria-describedby={
                              noteError ? "note-error" : undefined
                            }
                            placeholder="Add evidence: address, branch or independent confirmation…"
                            value={note}
                            onChange={(e) => {
                              N(e.target.value);
                              NE(false);
                            }}
                          />
                          {noteError && (
                            <p
                              id="note-error"
                              role="alert"
                              className="field-error"
                            >
                              Add an evidence note before recording your
                              decision.
                            </p>
                          )}
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
                        </div>
                      </>
                    ) : (
                      <div className="empty">
                        Select a pair to inspect source evidence.
                      </div>
                    )}
                    {p && (
                      <details className="locationdetails">
                        <summary>Location & review checklist</summary>
                        <div className="locationbody">
                          <h3>Location context</h3>
                          <div className="map">
                            <div className="mapgrid" />
                            {p &&
                              hasCoordinates(p.a) &&
                              hasCoordinates(p.b) && (
                                <>
                                  <i
                                    className="pin pinA"
                                    style={pinStyle(p.a, p.b)}
                                  >
                                    A
                                  </i>
                                  <i
                                    className="pin pinB"
                                    style={pinStyle(p.b, p.a)}
                                  >
                                    B
                                  </i>
                                </>
                              )}
                            <span className="mapcaption">
                              RELATIVE COORDINATES
                            </span>
                          </div>
                          <p className="mapnote">
                            Coordinate schematic · no external tiles
                            <small>
                              Use source coordinates for exact location.
                            </small>
                          </p>
                          <hr />
                          <h3>Resolution checklist</h3>
                          <ul>
                            <li>Same physical address?</li>
                            <li>Separate branches nearby?</li>
                            <li>Renaming or relocation?</li>
                            <li>Enough independent evidence?</li>
                          </ul>
                          <h3>Provenance</h3>
                          <p className="muted">
                            Immutable source versions are checked on every
                            confirmation. Conflicting group constraints block a
                            merge.
                          </p>
                        </div>
                      </details>
                    )}
                  </div>
                  {p && (
                    <div className="decisiondock">
                      <p>
                        {busy
                          ? "Saving decision…"
                          : p.status !== "REVIEW"
                            ? "Decision recorded · undo from Entities"
                            : note.trim()
                              ? "Evidence note added"
                              : "Add an evidence note before deciding"}
                      </p>
                      <div className="actions">
                        <button
                          disabled={
                            busy ||
                            opening ||
                            loading ||
                            !impact?.context_version ||
                            impact.pair_id !== p.id ||
                            p.source_stale ||
                            p.status !== "REVIEW" ||
                            !!impact?.merge_blockers?.length
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
                            opening ||
                            loading ||
                            !impact?.context_version ||
                            impact.pair_id !== p.id ||
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
                            opening ||
                            loading ||
                            !impact?.context_version ||
                            impact.pair_id !== p.id ||
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
                  )}
                </section>
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
              <div className="exportbar">
                <div>
                  <h2>Canonical directory</h2>
                  <p className="muted">
                    Download up to 500 reviewed entities. JSON preserves field
                    provenance; CSV provides a flat directory.
                  </p>
                </div>
                <div className="actions">
                  <button
                    className="secondary"
                    disabled={
                      exporting || !entities.some((e) => !e.needs_review)
                    }
                    onClick={() => downloadEntities("json")}
                  >
                    <Download size={14} />
                    JSON
                  </button>
                  <button
                    className="secondary"
                    disabled={
                      exporting || !entities.some((e) => !e.needs_review)
                    }
                    onClick={() => downloadEntities("csv")}
                  >
                    <Download size={14} />
                    CSV
                  </button>
                </div>
              </div>
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
                    <div className="historydetail">
                      <strong>
                        {h.record_names?.join(" ↔ ") || h.pair_id}
                      </strong>
                      <p>{h.rationale}</p>
                      <time dateTime={new Date(h.created * 1000).toISOString()}>
                        {new Date(h.created * 1000).toLocaleString()} ·{" "}
                        {h.pair_id.slice(0, 8)}
                      </time>
                    </div>
                    <button
                      className="secondary"
                      disabled={busy || opening}
                      onClick={() => openPair(h.pair_id)}
                    >
                      <ExternalLink size={14} />
                      Open pair
                    </button>
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
            EntityLens <span>Entity resolution workspace</span>
            <span>NYC DOHMH · Overture Maps Foundation</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
