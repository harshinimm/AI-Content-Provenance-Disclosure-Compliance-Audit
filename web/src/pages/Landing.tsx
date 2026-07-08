import { Link } from "react-router-dom";
import { Reveal } from "../components/Reveal";
import styles from "./Landing.module.css";

const PIPELINE_STEPS = [
  {
    n: "01",
    title: "Scrape",
    body: "Crawl a company's site for images — same-domain, robots.txt-respecting, static HTML only.",
  },
  {
    n: "02",
    title: "Triage",
    body: "Run every image through an AI-generation classifier. Only flagged images continue — this is what makes checking hundreds of images tractable.",
  },
  {
    n: "03",
    title: "Check",
    body: "Read C2PA manifests. Run a SynthID watermark estimate. Log what's actually embedded, not what's claimed.",
  },
  {
    n: "04",
    title: "Transform",
    body: "Screenshot, recompress, crop, resize — the same casual edits any image survives on its way around the internet.",
  },
  {
    n: "05",
    title: "Re-check",
    body: "Run the same checks again. Does the disclosure signal survive, or does it quietly disappear?",
  },
  {
    n: "06",
    title: "Score",
    body: "Two independent verdicts — EU AI Act Article 50(2) and California SB 942 — plus an IP/copyright exposure flag.",
  },
];

export function Landing() {
  return (
    <main>
      <section className={styles.hero}>
        <div className={`container ${styles.heroInner}`}>
          <span className={`mono ${styles.eyebrow}`}>
            provenance &amp; disclosure compliance audit
          </span>
          <h1 className={styles.heroTitle}>
            The law assumes AI disclosure marks survive.
            <br />
            <span className={styles.heroAccent}>We tested that.</span>
          </h1>
          <p className={styles.heroSub}>
            EU AI Act Article 50(2) and California SB 942 both require
            AI-generated images to carry machine-readable disclosure — and
            for that disclosure to be robust, not incidental. This audit
            scrapes real company sites, triages which images are likely
            AI-generated, and tests whether their disclosure signals
            actually survive a screenshot, a recompress, a crop, a resize.
          </p>
          <div className={styles.heroActions}>
            <Link to="/results" className={styles.primaryButton}>
              View results ↗
            </Link>
            <a
              href="https://github.com/harshinimm/AI-Content-Provenance-Disclosure-Compliance-Audit"
              target="_blank"
              rel="noreferrer"
              className={styles.secondaryButton}
            >
              Read the methodology
            </a>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className="container">
          <Reveal>
            <span className={`mono ${styles.sectionLabel}`}>the law</span>
            <h2 className={styles.sectionTitle}>
              Two statutes, two different bars
            </h2>
          </Reveal>
          <div className={styles.lawGrid}>
            <Reveal className={styles.lawCard}>
              <h3>EU AI Act — Article 50(2)</h3>
              <p>
                Synthetic content must be marked in a machine-readable
                format, detectable as artificially generated. The marking
                must be <em>"effective, robust, reliable, and
                interoperable, as far as technically feasible."</em>{" "}
                Effective August 2, 2026.
              </p>
            </Reveal>
            <Reveal className={styles.lawCard}>
              <h3>California SB 942</h3>
              <p>
                Applies to image, video, and audio from "Covered Providers"
                — systems with over 1M monthly CA users. Requires latent
                disclosure that's <em>"permanent or extraordinarily
                difficult to remove."</em> A stricter bar than the EU's.
                Already in effect.
              </p>
            </Reveal>
          </div>
        </div>
      </section>

      <section className={`${styles.section} ${styles.sectionDark}`}>
        <div className="container">
          <Reveal>
            <span className={`mono ${styles.sectionLabel}`}>
              the method
            </span>
            <h2 className={styles.sectionTitle}>Six steps, per image</h2>
          </Reveal>
          <div className={styles.pipeline}>
            {PIPELINE_STEPS.map((step) => (
              <Reveal key={step.n} className={styles.pipelineStep}>
                <span className={`mono ${styles.pipelineN}`}>{step.n}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className="container">
          <Reveal>
            <span className={`mono ${styles.sectionLabel}`}>
              first findings
            </span>
            <h2 className={styles.sectionTitle}>
              What we found auditing elevenlabs.io
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
