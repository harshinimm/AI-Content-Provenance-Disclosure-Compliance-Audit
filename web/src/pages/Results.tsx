import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import { VerdictBadge } from "../components/VerdictBadge";
import {
  shortSource,
  verdictTone,
  type ResultRow,
  type VerdictTone,
} from "../lib/types";
import styles from "./Results.module.css";

const FILTERS: { label: string; tone: VerdictTone | "all" }[] = [
  { label: "All", tone: "all" },
  { label: "Likely Compliant", tone: "compliant" },
  { label: "Gap", tone: "gap" },
  { label: "Non-Compliant", tone: "noncompliant" },
  { label: "Not Applicable", tone: "na" },
];

export function Results() {
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [filter, setFilter] = useState<VerdictTone | "all">("all");

  useEffect(() => {
    Papa.parse<Record<string, string>>("/data/results.csv", {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (parsed) => {
        const mapped = parsed.data.map(
          (r): ResultRow => ({
            source: r["source"] ?? "",
            tool: r["tool"] ?? "",
            c2pa: r["C2PA pre/post"] ?? "",
            synthid: r["SynthID pre/post"] ?? "",
            dire: r["DIRE pre/post"] ?? "",
            article50: r["Article 50 verdict"] ?? "",
            sb942: r["SB 942 verdict"] ?? "",
            ipFlag: r["IP flag"] ?? "",
          }),
        );
        setRows(mapped);
        setStatus("ready");
      },
      error: () => setStatus("error"),
    });
  }, []);

  const filtered = useMemo(
    () =>
      filter === "all"
        ? rows
        : rows.filter((r) => verdictTone(r.article50) === filter),
    [rows, filter],
  );

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of rows) {
      const tone = verdictTone(r.article50);
      c[tone] = (c[tone] ?? 0) + 1;
    }
    return c;
  }, [rows]);

  return (
    <main className={`container ${styles.page}`}>
      <header className={styles.header}>
        <span className="mono">results</span>
        <h1>Per-image audit output</h1>
        <p>
          Raw output from <code>output/results.csv</code> — every scraped
          image DIRE flagged as likely AI-generated, checked for C2PA/
          SynthID signals before and after a screenshot/recompress/crop/
          resize battery.{" "}
          {rows.length > 0 && (
            <>
              {rows.length} images scraped, targeting{" "}
              <strong>{rows[0]?.tool}</strong>.
            </>
          )}
        </p>
      </header>

      {status === "loading" && <p>Loading results…</p>}
      {status === "error" && (
        <p>
          Couldn't load <code>/data/results.csv</code>. Copy a fresh export
          from <code>output/results.csv</code> into{" "}
          <code>web/public/data/results.csv</code>.
        </p>
      )}

      {status === "ready" && (
        <>
          <div className={styles.filters}>
            {FILTERS.map((f) => (
              <button
                key={f.label}
                className={`${styles.filterButton} ${
                  filter === f.tone ? styles.filterActive : ""
                }`}
                onClick={() => setFilter(f.tone)}
              >
                {f.label}
                {f.tone !== "all" && (
                  <span className={styles.filterCount}>
                    {counts[f.tone] ?? 0}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>C2PA pre/post</th>
                  <th>SynthID pre/post</th>
                  <th>DIRE pre/post</th>
                  <th>Article 50</th>
                  <th>SB 942</th>
                  <th>IP flag</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row, i) => (
                  <tr key={i}>
                    <td className="mono">{shortSource(row.source)}</td>
                    <td className="mono">{row.c2pa}</td>
                    <td className="mono">{row.synthid}</td>
                    <td className="mono">{row.dire}</td>
                    <td>
                      <VerdictBadge verdict={row.article50} />
                    </td>
                    <td>
                      <VerdictBadge verdict={row.sb942} />
                    </td>
                    <td>{row.ipFlag}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
