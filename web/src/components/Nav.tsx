import { Link, useLocation } from "react-router-dom";
import styles from "./Nav.module.css";

export function Nav() {
  const location = useLocation();

  return (
    <header className={styles.nav}>
      <div className={`container ${styles.inner}`}>
        <Link to="/" className={styles.logo}>
          <span className={styles.logoMark} />
          <span className="mono">provenance&nbsp;audit</span>
        </Link>
        <nav className={styles.links}>
          <Link
            to="/"
            className={location.pathname === "/" ? styles.active : undefined}
          >
            Overview
          </Link>
          <Link
            to="/results"
            className={
              location.pathname === "/results" ? styles.active : undefined
            }
          >
            Results
          </Link>
          <a
            href="https://github.com/harshinimm/AI-Content-Provenance-Disclosure-Compliance-Audit"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}
