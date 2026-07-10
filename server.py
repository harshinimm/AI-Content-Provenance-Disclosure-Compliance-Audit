"""API server wrapping the audit pipeline for the web frontend.

Local dev:
    uvicorn server:app --reload --port 8000

Deployed (e.g. Railway): set ALLOWED_ORIGINS to your Vercel frontend's
URL and JOBS_DIR to a mounted persistent volume — see README.

Still no real auth — this is a personal-project deployment, not a
multi-tenant SaaS. Two things are hardened regardless, since "scrape
whatever URL a caller supplies" is a real SSRF vector the moment this
is reachable from the public internet, not just a localhost caveat:
  - _resolve_and_validate_host() blocks loopback/private/link-local
    targets (including cloud metadata endpoints like 169.254.169.254)
    before any scrape starts.
  - A simple per-IP in-memory rate limit on POST /api/audits (audits
    are expensive — real DIRE/SynthID/C2PA checks — so even a basic
    limiter meaningfully raises the bar against casual abuse).
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import threading
import time
import urllib.parse as urlparse
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from audit.pipeline import ImageAuditRow, run_image
from audit.scraper import scrape_images
from audit.synthid import METHOD_UNOFFICIAL

JOBS_DIR = Path(os.environ.get("JOBS_DIR", "output/web_jobs"))
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_and_validate_host(url: str) -> None:
    """Reject scrape targets that resolve to loopback/private/link-local
    addresses (SSRF guard). Raises HTTPException on rejection.
    """
    hostname = urlparse.urlparse(url).hostname
    if not hostname:
        raise HTTPException(400, "url has no hostname")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(400, f"couldn't resolve host: {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(400, "url resolves to a private/internal address, not allowed")


_RATE_LIMIT_WINDOW_SECONDS = 3600
_RATE_LIMIT_MAX_REQUESTS = 10
_rate_limit_log: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    log = _rate_limit_log[client_ip]
    log[:] = [t for t in log if now - t < _RATE_LIMIT_WINDOW_SECONDS]
    if len(log) >= _RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(429, "Too many audits from this IP — try again later.")
    log.append(now)


def _fmt_synthid(detected: bool | None, method: str) -> str:
    if detected is None:
        return "N/A"
    suffix = " (unofficial)" if method == METHOD_UNOFFICIAL else ""
    return f"{detected}{suffix}"


def _row_to_dict(job_id: str, row: ImageAuditRow) -> dict:
    filename = Path(row.source).name
    return {
        "source": filename,
        "imageUrl": f"/api/audits/{job_id}/images/{filename}",
        "tool": row.tool,
        "c2pa": f"{row.c2pa_pre}/{row.c2pa_post}",
        "synthid": (
            f"{_fmt_synthid(row.synthid_pre, row.synthid_pre_method)}/"
            f"{_fmt_synthid(row.synthid_post, row.synthid_post_method)}"
        ),
        "dire": f"{row.dire_pre}/{row.dire_post}",
        "article50": row.article50_verdict,
        "sb942": row.sb942_verdict,
        "ipFlag": row.ip_flag,
    }


@dataclass
class JobState:
    id: str
    url: str
    status: Literal["scraping", "auditing", "done", "error"] = "scraping"
    total: int = 0
    completed: int = 0
    rows: list[dict] = field(default_factory=list)
    error: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# In-memory cache for jobs from this process's lifetime, so hot polling
# doesn't hit disk every ~2s. Jobs also persist to JOBS_DIR/<id>/job.json
# so past runs survive a server restart (see _list_jobs/_load_job).
JOBS: dict[str, JobState] = {}


def _persist(job: JobState) -> None:
    job_dir = JOBS_DIR / job.id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(asdict(job)))


def _load_job(job_id: str) -> JobState | None:
    if job_id in JOBS:
        return JOBS[job_id]
    path = JOBS_DIR / job_id / "job.json"
    if not path.is_file():
        return None
    job = JobState(**json.loads(path.read_text()))
    JOBS[job_id] = job
    return job


def _list_jobs() -> list[dict]:
    if not JOBS_DIR.is_dir():
        return []
    summaries = []
    for job_dir in JOBS_DIR.iterdir():
        job_file = job_dir / "job.json"
        if not job_file.is_file():
            continue
        try:
            data = json.loads(job_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        summaries.append(
            {
                "id": data["id"],
                "url": data["url"],
                "status": data["status"],
                "total": data["total"],
                "completed": data["completed"],
                "startedAt": data.get("started_at"),
            }
        )
    summaries.sort(key=lambda s: s["startedAt"] or "", reverse=True)
    return summaries


class StartAuditRequest(BaseModel):
    url: str
    max_pages: int = 8
    max_images: int = 12


def _run_job(job: JobState, max_pages: int, max_images: int) -> None:
    job_dir = JOBS_DIR / job.id
    scraped_dir = job_dir / "scraped"
    try:
        scraped = scrape_images(job.url, scraped_dir, max_pages=max_pages, max_images=max_images)
        job.total = len(scraped)
        if not scraped:
            job.status = "error"
            job.error = "No images found (or all disallowed by robots.txt / unreachable)."
            _persist(job)
            return

        job.status = "auditing"
        _persist(job)
        domain = urlparse.urlparse(job.url).netloc
        for scraped_image in scraped:
            row = run_image(scraped_image.local_path, tool=domain)
            job.rows.append(_row_to_dict(job.id, row))
            job.completed += 1
            _persist(job)
        job.status = "done"
        _persist(job)
    except Exception as exc:  # noqa: BLE001 — surface any failure to the poller
        job.status = "error"
        job.error = str(exc)
        _persist(job)


@app.post("/api/audits")
def start_audit(req: StartAuditRequest, request: Request) -> dict:
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(400, "url must start with http:// or https://")

    _check_rate_limit(request.client.host if request.client else "unknown")
    _resolve_and_validate_host(req.url)

    job_id = uuid.uuid4().hex[:8]
    job = JobState(id=job_id, url=req.url)
    JOBS[job_id] = job
    _persist(job)

    thread = threading.Thread(
        target=_run_job, args=(job, req.max_pages, req.max_images), daemon=True
    )
    thread.start()
    return {"jobId": job_id}


@app.get("/api/audits")
def list_audits() -> list[dict]:
    return _list_jobs()


@app.get("/api/audits/{job_id}")
def get_audit(job_id: str) -> dict:
    job = _load_job(job_id)
    if job is None:
        raise HTTPException(404, "unknown job id")
    return {
        "id": job.id,
        "url": job.url,
        "status": job.status,
        "total": job.total,
        "completed": job.completed,
        "rows": job.rows,
        "error": job.error,
    }


@app.get("/api/audits/{job_id}/images/{filename}")
def get_image(job_id: str, filename: str) -> FileResponse:
    scraped_dir = (JOBS_DIR / job_id / "scraped").resolve()
    path = (scraped_dir / filename).resolve()
    # filename is caller-supplied; confirm the resolved path didn't escape
    # scraped_dir via ".." before trusting it (path-traversal guard).
    if scraped_dir not in path.parents or not path.is_file():
        raise HTTPException(404, "image not found")
    return FileResponse(path)
