import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Reveal } from "../components/Reveal";
import { startAudit } from "../lib/api";
import styles from "./Overview.module.css";

const DEFAULT_MAX_PAGES = 8;
const DEFAULT_MAX_IMAGES = 12;

export function Overview() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(DEFAULT_MAX_PAGES);
  const [maxImages, setMaxImages] = useState(DEFAULT_MAX_IMAGES);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    let target = url.trim();
    if (target && !/^https?:\/\//i.test(target)) {
      target = `https://${target}`;
    }
    if (!target) {
      setError("Enter a URL first.");
      return;
    }

    setSubmitting(true);
    try {
      const { jobId } = await startAudit(
        target,
        Math.max(1, maxPages),
        Math.max(1, maxImages),
      );
      navigate(`/results?job=${jobId}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Couldn't start the audit — is the local API server running (uvicorn server:app --port 8000)?",
      );
      setSubmitting(false);
    }
  }

  return (
    <main>
      <section className={styles.hero}>
        <div className={`container ${styles.heroInner}`}>
          <span className={`mono ${styles.eyebrow}`}>
            self-audit: AI disclosure compliance
          </span>
          <h1 className={styles.heroTitle}>
            Find out before a regulator does.
            <br />
            <span className={styles.heroAccent}>Check your own site.</span>
          </h1>
          <p className={styles.heroSub}>
            EU AI Act Article 50(2) and California SB 942 both require
            AI-generated images to carry machine-readable disclosure — and
            for that disclosure to survive normal handling, not just exist
            once at upload. Enter your site's URL to scrape it, triage
            which images are likely AI-generated, and test whether your
            disclosure signals actually survive a screenshot, a
            recompress, a crop, a resize — with concrete next steps for
            anything that doesn't.
          </p>

          <form className={styles.form} onSubmit={handleSubmit}>
            <input
              type="text"
              className={styles.input}
              placeholder="example-company.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={submitting}
            />
            <button
              type="submit"
              className={styles.primaryButton}
              disabled={submitting}
            >
              {submitting ? "Starting…" : "Run audit ↗"}
            </button>
          </form>
          {error && <p className={styles.error}>{error}</p>}

          <details className={styles.advanced}>
            <summary>Advanced options</summary>
            <div className={styles.advancedFields}>
              <label>
                Max pages to crawl
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  disabled={submitting}
                />
              </label>
              <label>
                Max images to check
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={maxImages}
                  onChange={(e) => setMaxImages(Number(e.target.value))}
                  disabled={submitting}
                />
              </label>
            </div>
          </details>

          <p className={styles.formHint}>
            Runs a crawl ({maxPages} page{maxPages === 1 ? "" : "s"},{" "}
            {maxImages} image{maxImages === 1 ? "" : "s"}) against the local
            API server — takes a few minutes since each flagged image gets
            a real DIRE + SynthID + C2PA check. Higher numbers take
            proportionally longer.
          </p>

          <div className={styles.heroActions}>
            <Link to="/results" className={styles.secondaryButton}>
              See an example run ↗
            </Link>
            <Link to="/info" className={styles.secondaryButton}>
              How it works
            </Link>
          </div>

          <p className={styles.disclaimer}>
            <strong>Not legal advice.</strong> Verdicts are an automated,
            best-effort reading of Article 50(2)/SB 942 against signals this
            tool can detect — several of which are explicitly unofficial
            estimates (see <Link to="/info">Info</Link>). Treat results as a
            starting point for your own review, not a compliance
            determination. Talk to counsel before making representations
            based on this output.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <div className="container">
          <Reveal>
            <span className={`mono ${styles.sectionLabel}`}>
              what a run looks like
            </span>
            <h2 className={styles.sectionTitle}>
              Example output from a real audit (elevenlabs.io)
            </h2>
          </Reveal>
          <div className={styles.statGrid}>
            <Reveal className={styles.statCard}>
              <span className={styles.statNumber}>0 / 15</span>
              <p>scraped images carried a C2PA manifest</p>
            </Reveal>
            <Reveal className={styles.statCard}>
              <span className={styles.statNumber}>13 / 15</span>
              <p>flagged as likely AI-generated by the triage gate</p>
            </Reveal>
            <Reveal className={styles.statCard}>
              <span className={styles.statNumber}>~83%</span>
              <p>
                of images with a detected watermark lost that signal after
                one basic edit
              </p>
            </Reveal>
          </div>
          <Reveal className={styles.caveat}>
            <p>
              <strong>Read this carefully before citing it:</strong> the
              watermark check is an unofficial, third-party estimate
              trained only on GPT-Image-2 — not Google's own SynthID
              verifier, and unproven on other generators' output. Treat
              these numbers as evidence the pipeline works, not as a
              confirmed claim about any one company.{" "}
              <Link to="/results">See the full per-image breakdown →</Link>
            </p>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
