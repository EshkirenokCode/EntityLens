import { Fragment } from "react";

export type SourceRecord = {
  id: string;
  name: string;
  address: string;
  source: string;
  lat: number | null;
  lon: number | null;
  phone: string;
  version: string;
};
const displayKey = (value: string) =>
  value.normalize("NFKC").trim().replace(/\s+/g, " ").toLocaleLowerCase("en");
const coordinates = (r: SourceRecord) =>
  typeof r.lat === "number" &&
  typeof r.lon === "number" &&
  Number.isFinite(r.lat) &&
  Number.isFinite(r.lon) &&
  Math.abs(r.lat) <= 90 &&
  Math.abs(r.lon) <= 180
    ? `${r.lat.toFixed(5)}, ${r.lon.toFixed(5)}`
    : "";

export function RecordComparison({
  a,
  b,
}: {
  a: SourceRecord;
  b: SourceRecord;
}) {
  const fields = [
    { label: "Place name", values: [a.name, b.name], name: true },
    { label: "Address", values: [a.address, b.address] },
    { label: "Phone", values: [a.phone, b.phone], mono: true },
    { label: "Location", values: [coordinates(a), coordinates(b)], mono: true },
  ];
  return (
    <>
      <table className="recordtable" aria-label="Source record comparison">
        <colgroup>
          <col className="propertycol" />
          <col />
          <col />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Source field</th>
            {[a, b].map((r, i) => (
              <th scope="col" key={r.id}>
                <span className={`sourcebadge source-${i}`}>
                  <span>{i ? "B" : "A"}</span>
                  {r.source === "nyc" ? "NYC DOHMH" : "Overture Places"}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fields.map(({ label, values, name, mono }) => {
            const differs =
              values.every(Boolean) &&
              displayKey(values[0]) !== displayKey(values[1]);
            return (
              <tr key={label} className={differs ? "differentfield" : ""}>
                <th scope="row">
                  {label}
                  {differs && <small>Values differ</small>}
                </th>
                {values.map((v, i) => (
                  <td
                    key={i}
                    className={`${name ? "recordname" : ""} ${mono ? "monovalue" : ""}`}
                  >
                    {v || <span className="missingvalue">Not provided</span>}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      <details className="recordmeta">
        <summary>Source identifiers & versions</summary>
        <dl>
          {[a, b].map((r, i) => (
            <Fragment key={r.id}>
              <dt>Source {i ? "B" : "A"}</dt>
              <dd>
                {r.id}
                <small>Version {r.version}</small>
              </dd>
            </Fragment>
          ))}
        </dl>
        <p>
          Highlighted differences compare displayed values only; they do not
          establish place identity.
        </p>
      </details>
    </>
  );
}
