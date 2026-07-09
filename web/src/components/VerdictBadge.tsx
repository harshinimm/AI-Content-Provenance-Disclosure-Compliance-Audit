import { verdictTone } from "../lib/types";
import styles from "./VerdictBadge.module.css";

const LABELS: Record<string, string> = {
  na: "Not Applicable",
  compliant: "Likely Compliant",
  gap: "Gap",
  noncompliant: "Non-Compliant",
};

export function VerdictBadge({
  verdict,
  law,
}: {
  verdict: string;
  law: "EU Art. 50" | "CA SB 942";
}) {
  const tone = verdictTone(verdict);
  return (
    <span className={`${styles.badge} ${styles[tone]}`} title={verdict}>
      <span className={styles.law}>{law}</span>
      {LABELS[tone]}
    </span>
  );
}
