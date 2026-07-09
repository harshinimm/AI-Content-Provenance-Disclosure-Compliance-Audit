import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Papa from "papaparse";
import { VerdictBadge } from "../components/VerdictBadge";
import {
  getAudit,
  imageUrl,
  listAudits,
  type AuditJob,
  type AuditSummary,
} from "../lib/api";
import {
  formatDire,
  shortSource,
  verdictTone,
  type ResultRow,
  type VerdictTone,
} from "../lib/types";
import styles from "./Results.module.css";

const EXAMPLE_VALUE = "__example__";

function summaryLabel(a: AuditSummary): string {
  const host = a.url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  const progress =
    a.status === "done"
      ? `${a.completed}/${a.total} done`
      : a.status === "error"
        ? "error"
        : `${a.completed}/${a.total || "?"} running…`;
  return `${host} — ${progress}`;
}

const FILTERS: { label: string; tone: VerdictTone | "all" }[] = [
  { label: "All", tone: "all" },
  { label: "Likely Compliant", tone: "compliant" },
  { label: "Gap", tone: "gap" },
  { label: "Non-Compliant", tone: "noncompliant" },
  { label: "Not Applicable", tone: "na" },
];

function jobRowToResultRow(row: AuditJob["rows"][number]): ResultRow & {
  image: string;
} {
  return {
    source: row.source,
    tool: row.tool,
    c2pa: row.c2pa,
    synthid: row.synthid,
    dire: row.dire,
    article50: row.article50,
    sb942: row.sb942,
    ipFlag: row.ipFlag,
    image: imageUrl(row.imageUrl),
  };
}

export function Results() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get("job");

  const [rows, setRows] = useState<(ResultRow & { image: string })[]>([]);
  const [job, setJob] = useState<AuditJob | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [filter, setFilter] = useState<VerdictTone | "all">("all");
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const pollRef = useRef<number | null>(null);

  // Every past (and in-progress) run, for the "which company" dropdown —
  // refetched whenever the selected job finishes, so a freshly-completed
  // run's final counts show up without needing a manual page reload.
  useEffect(() => {
    listAudits()
      .then(setAudits)
      .catch(() => {
        /* dropdown just stays empty except the bundled example — non-fatal */
      });
  }, [jobId, job?.status]);

  // Static example dataset — no job param, no live backend needed.
  useEffect(() => {
    if (jobId) return;
    Papa.parse<Record<string, string>>("/data/results.csv", {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (parsed) => {
        const mapped = parsed.data.map((r) => {
          const filename = shortSource(r["source"] ?? "");
          return {
            source: r["source"] ?? "",
            tool: r["tool"] ?? "",
            c2pa: r["C2PA pre/post"] ?? "",
            synthid: r["SynthID pre/post"] ?? "",
            dire: r["DIRE pre/post"] ?? "",
            article50: r["Article 50 verdict"] ?? "",
            sb942: r["SB 942 verdict"] ?? "",
            ipFlag: r["IP flag"] ?? "",
            image: `/data/images/${filename}`,
          };
        });
        setRows(mapped);
        setStatus("ready");
      },
      error: () => setStatus("error"),
    });
  }, [jobId]);

  // Live job — poll the backend until it's done.
  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;

    async function poll() {
      try {
        const data = await getAudit(jobId!);
        if (cancelled) return;
        setJob(data);
        setRows(data.rows.map(jobRowToResultRow));
        if (data.status === "done") {
          setStatus("ready");
        } else if (data.status === "error") {
          setStatus("error");
          setErrorMsg(data.error);
        } else {
          setStatus("ready"); // show partial rows as they stream in
          pollRef.current = window.setTimeout(poll, 2000);
        }
      } catch (err) {
        if (cancelled) return;
        setStatus("error");
        setErrorMsg(err instanceof Error ? err.message : "Failed to load job");
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [jobId]);

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

  const isLive = Boolean(jobId);
  const isRunning = job && job.status !== "done" && job.status !== "error";

  function handlePick(value: string) {
    if (value === EXAMPLE_VALUE) {
      navigate("/results");
    } else {
      navigate(`/results?job=${value}`);
    }
  }

  return (
    <main className={`container ${styles.page}`}>
      <header className={styles.header}>
        <span className="mono">results</span>
        <h1>
          {isLive ? "Live audit run" : "Example: elevenlabs.io"}
        </h1>

        {audits.length > 0 && (
          <select
            className={styles.picker}
            value={jobId ?? EXAMPLE_VALUE}
            onChange={(e) => handlePick(e.target.value)}
          >
            <option value={EXAMPLE_VALUE}>Example: elevenlabs.io</option>
            {audits.map((a) => (
              <option key={a.id} value={a.id}>
                {summaryLabel(a)}
              </option>
            ))}
          </select>
        )}

        <p>
          {isLive ? (
            job ? (
              <>
                Auditing <strong>{job.url}</strong> —{" "}
                {job.status === "scraping" && "crawling for images…"}
                {job.status === "auditing" &&
                  `checked ${job.completed} of ${job.total} flagged images…`}
                {job.status === "done" &&
                  `${job.rows.length} image(s) DIRE flagged as likely AI-generated, checked for C2PA/SynthID signals before and after a transform battery.`}
              </>
            ) : (
              "Starting audit…"
            )
          ) : (
            <>
              Raw output from a real run — every scraped image DIRE flagged
              as likely AI-generated, checked for C2PA/SynthID signals
              before and after a screenshot/recompress/crop/resize battery.
              {rows.length > 0 && (
                <>
                  {" "}
                  {rows.length} images scraped, targeting{" "}
                  <strong>{rows[0]?.tool}</strong>.
                </>
              )}
            </>
          )}
        </p>
      </header>

      {status === "loading" && <p>Loading results…</p>}
      {status === "error" && (
        <p className={styles.errorText}>
          {errorMsg ??
            "Couldn't load results. If this was a live run, the audit job may have failed."}
        </p>
      )}

      {isRunning && (
        <div className={styles.progress}>
          <div
            className={styles.progressBar}
            style={{
              width: job.total
                ? `${(job.completed / job.total) * 100}%`
                : "8%",
            }}
          />
        </div>
      )}

      {(status === "ready" || isRunning) && rows.length > 0 && (
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

          <div className={styles.grid}>
            {filtered.map((row, i) => (
              <article key={i} className={styles.card}>
                <div className={styles.thumbWrap}>
                  <img
                    src={row.image}
                    alt=""
                    className={styles.thumb}
                    loading="lazy"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display =
                        "none";
                    }}
                  />
                </div>
                <div className={styles.cardBody}>
                  <p className={`mono ${styles.cardSource}`}>
                    {shortSource(row.source)}
                  </p>
                  <div className={styles.badgeRow}>
                    <VerdictBadge verdict={row.article50} law="EU Art. 50" />
                    <VerdictBadge verdict={row.sb942} law="CA SB 942" />
                  </div>
                  <dl className={styles.cardMeta}>
                    <dt>C2PA</dt>
                    <dd className="mono">{row.c2pa}</dd>
                    <dt>SynthID</dt>
                    <dd className="mono">{row.synthid}</dd>
                    <dt>DIRE</dt>
                    <dd className="mono">
                      {(() => {
                        const dire = formatDire(row.dire);
                        return (
                          <details className={styles.direToggle}>
                            <summary>
                              {dire.preLabel}
                              {dire.postLabel !== dire.preLabel &&
                                dire.postLabel !== "N/A" &&
                                ` → ${dire.postLabel}`}
                            </summary>
                            <span className={styles.direRaw}>
                              score: {dire.raw}
                            </span>
                          </details>
                        );
                      })()}
                    </dd>
                    <dt>IP flag</dt>
                    <dd>{row.ipFlag}</dd>
                  </dl>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
