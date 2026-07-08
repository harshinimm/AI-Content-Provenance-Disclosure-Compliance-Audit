import styles from "./Footer.module.css";

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <p className={styles.copy}>
          A research audit testing whether AI content-disclosure signals
          (C2PA, SynthID) survive real-world edits — and what the law
          actually requires vs. what's true in practice.
        </p>
        <div className={styles.meta}>
          <span className="mono">EU AI Act Art. 50(2)</span>
          <span className="mono">CA SB 942</span>
          <a
            href="https://github.com/harshinimm/AI-Content-Provenance-Disclosure-Compliance-Audit"
            target="_blank"
            rel="noreferrer"
          >
            Source on GitHub ↗
          </a>
        </div>
      </div>
    </footer>
  );
}
