import { verdictTone } from "../lib/types";
import styles from "./VerdictBadge.module.css";

const LABELS: Record<string, string> = {
  na: "Not Applicable",
  compliant: "Likely Compliant",
  gap: "Gap",
  noncompliant: "Non-Compliant",
};

export function VerdictBadge({ verdict }: { verdict: string }) {
  const tone = verdictTone(verdict);
  return (
    <span
      className={`${styles.badge} ${styles[tone]}`}
      title={verdict}
    >
      {LABELS[tone]}
    </span>
  );
}
