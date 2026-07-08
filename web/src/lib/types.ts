export interface ResultRow {
  source: string;
  tool: string;
  c2pa: string;
  synthid: string;
  dire: string;
  article50: string;
  sb942: string;
  ipFlag: string;
}

export type VerdictTone = "compliant" | "gap" | "noncompliant" | "na";

export function verdictTone(verdict: string): VerdictTone {
  if (verdict.startsWith("Not Applicable")) return "na";
  if (verdict.startsWith("Likely Compliant")) return "compliant";
  if (verdict.includes("Gap")) return "gap";
  return "noncompliant";
}

export function shortSource(source: string): string {
  return source.split(/[/\\]/).pop() ?? source;
}
