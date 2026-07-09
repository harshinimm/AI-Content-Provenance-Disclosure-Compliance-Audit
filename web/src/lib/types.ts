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

export interface DireSummary {
  preLabel: string;
  postLabel: string;
  raw: string;
}

// "0.9999/0.999725" -> AI-generated Yes/Yes, but keep the raw score
// available behind a toggle for anyone who wants the actual number
// rather than just the >0.5 threshold call.
export function formatDire(dire: string): DireSummary {
  const [preRaw, postRaw] = dire.split("/");
  const label = (v: string) => {
    const n = Number(v);
    if (v === "None" || Number.isNaN(n)) return "N/A";
    return n > 0.5 ? "AI-generated" : "Not AI-generated";
  };
  return { preLabel: label(preRaw), postLabel: label(postRaw), raw: dire };
}
