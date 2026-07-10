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

export interface IPFlagChip {
  label: string;
  explanation: string;
}

const IP_FLAG_EXPLANATIONS: Record<string, string> = {
  "Copyrightability Risk":
    "This image has no C2PA authorship/rights metadata at all, on a site assumed to claim copyright over its content. Purely AI-generated content without meaningful human authorship may not be copyrightable in several jurisdictions (e.g. US Copyright Office guidance) — so that copyright claim may not actually hold for this image.",
  "Lost Attribution Chain":
    "This image did carry C2PA rights/licensing metadata before the transform battery (screenshot/recompress/crop/resize), but it didn't survive. Even when rights metadata is embedded correctly, ordinary image handling can strip it.",
};

export function parseIpFlags(ipFlag: string): IPFlagChip[] {
  if (!ipFlag || ipFlag === "None") return [];
  return ipFlag.split(";").map((raw) => {
    const label = raw.trim();
    return {
      label,
      explanation: IP_FLAG_EXPLANATIONS[label] ?? label,
    };
  });
}

const REMEDIATION: Record<VerdictTone, string | null> = {
  compliant: null,
  gap: "A disclosure signal was present but didn't survive your image pipeline (CDN recompression, cropping, resizing). Re-embed C2PA metadata after any processing step, not just at generation time, or use a watermarking method documented as robust to those specific transforms.",
  noncompliant:
    "No disclosure signal was detected at all. If this image is AI-generated, add a C2PA manifest (see contentauth.org for tooling) and/or a watermark at generation time — most modern generators (Adobe Firefly, OpenAI, Google) support this natively.",
  na: null,
};

export function remediationFor(verdict: string): string | null {
  return REMEDIATION[verdictTone(verdict)];
}
