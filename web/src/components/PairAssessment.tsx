import { Check, HelpCircle, AlertTriangle } from "lucide-react";
export type Finding = { code: string; message: string; records: string[] };
export type Evidence = {
  distance_m: number | null;
  signals: string[];
  warnings: string[];
  missing: { field: string; message: string; records: string[] }[];
  score_disagreement: number | null;
  model: string;
  basis: string;
  policy: string;
};
export type GroupImpact = {
  pair_id: string;
  context_version: string;
  members: { id: string; name: string; address: string; version: string }[];
  merge_blockers: Finding[];
  evidence: Evidence;
};
export function PairAssessment({
  evidence,
  blockers,
  model,
  score,
  baseline,
}: {
  evidence: Evidence;
  blockers: Finding[];
  model?: string;
  score: number;
  baseline: number;
}) {
  return (
    <section className="observations" aria-label="Pair assessment">
      <div className="assessmenthead">
        <h3>What the sources tell us</h3>
        <span>
          {evidence.distance_m === null
            ? "Distance unavailable"
            : `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(evidence.distance_m)} m apart`}
        </span>
      </div>
      <p className="muted">
        Observed facts, not a calibrated match probability.
      </p>
      <div className="scorecompare">
        <span>
          {model ? "Model" : "Rule"} score <b>{score.toFixed(3)}</b>
        </span>
        {model && (
          <span>
            Rule baseline <b>{baseline.toFixed(3)}</b>
          </span>
        )}
      </div>
      <ul>
        {evidence.signals.map((text) => (
          <li className="signal" key={text}>
            <Check size={13} />
            {text}
          </li>
        ))}
        {evidence.warnings.map((text) => (
          <li className="warning" key={text}>
            <AlertTriangle size={13} />
            {text}
          </li>
        ))}
        {evidence.missing.map((item) => (
          <li className="missing" key={item.field}>
            <HelpCircle size={13} />
            {item.message}
          </li>
        ))}
      </ul>
      {blockers?.length > 0 && (
        <div className="mergeblocked" role="status">
          <strong>Same place is blocked</strong>
          {blockers.map((item, i) => (
            <p key={i}>{item.message}</p>
          ))}
          <small>
            Different places and Unsure remain available for current proposals.
          </small>
        </div>
      )}
    </section>
  );
}
