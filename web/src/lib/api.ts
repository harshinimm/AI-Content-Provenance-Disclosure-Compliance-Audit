const API_BASE = "http://localhost:8000";

export interface AuditRow {
  source: string;
  imageUrl: string;
  tool: string;
  c2pa: string;
  synthid: string;
  dire: string;
  article50: string;
  sb942: string;
  ipFlag: string;
}

export interface AuditJob {
  id: string;
  url: string;
  status: "scraping" | "auditing" | "done" | "error";
  total: number;
  completed: number;
  rows: AuditRow[];
  error: string | null;
}

export async function startAudit(
  url: string,
  maxPages: number,
  maxImages: number,
): Promise<{ jobId: string }> {
  const res = await fetch(`${API_BASE}/api/audits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, max_pages: maxPages, max_images: maxImages }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export async function getAudit(jobId: string): Promise<AuditJob> {
  const res = await fetch(`${API_BASE}/api/audits/${jobId}`);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export function imageUrl(path: string): string {
  return `${API_BASE}${path}`;
}
