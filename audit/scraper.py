"""Step 0 — bulk collection: crawl a company site and download every image.

Same-domain breadth-first crawl, respects robots.txt, pulls <img src>,
<img srcset>, and inline style="background-image: url(...)" references.
Doesn't parse external CSS files or JS-rendered content — a static-HTML
crawl only, per the project guide's scope.
"""
from __future__ import annotations

import hashlib
import io
import time
import urllib.parse as urlparse
import urllib.robotparser as robotparser
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image

USER_AGENT = "ai-content-provenance-audit/0.1 (research tool; see README)"
REQUEST_DELAY_SECONDS = 0.5
TIMEOUT_SECONDS = 10
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@dataclass
class ScrapedImage:
    image_url: str
    page_url: str
    local_path: Path


def _load_robots(base_url: str, session: requests.Session) -> robotparser.RobotFileParser:
    parsed = urlparse.urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        resp = session.get(robots_url, timeout=TIMEOUT_SECONDS)
        rp.parse(resp.text.splitlines() if resp.ok else [])
    except requests.RequestException:
        rp.parse([])
    return rp


def _add_image_url(urls: set[str], page_url: str, raw: str) -> None:
    # data: URIs (e.g. Next.js blur-placeholder SVGs) aren't real fetchable
    # images — resolving one through urljoin just returns it unchanged
    # since it has its own scheme, so filter before that happens.
    if raw.startswith("data:"):
        return
    urls.add(urlparse.urljoin(page_url, raw))


def _extract_image_urls(html: str, page_url: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if isinstance(src, str):
            _add_image_url(urls, page_url, src)
        srcset = img.get("srcset") or img.get("data-srcset")
        if isinstance(srcset, str):
            for candidate in srcset.split(","):
                url = candidate.strip().split(" ")[0]
                if url:
                    _add_image_url(urls, page_url, url)

    for tag in soup.find_all(style=True):
        style_attr = tag.get("style")
        if isinstance(style_attr, str):
            start = style_attr.find("url(")
            if "background-image" in style_attr and start != -1:
                end = style_attr.find(")", start)
                raw = style_attr[start + 4 : end].strip("'\"")
                if raw:
                    _add_image_url(urls, page_url, raw)

    return urls


def _extract_page_links(html: str, page_url: str, domain: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        joined = urlparse.urljoin(page_url, a["href"]).split("#")[0]
        parsed = urlparse.urlparse(joined)
        if parsed.netloc == domain and parsed.scheme in ("http", "https"):
            links.add(joined)
    return links


def _download_image(
    session: requests.Session,
    image_url: str,
    output_dir: Path,
    index: int,
    seen_hashes: set[str],
) -> Path | None:
    try:
        resp = session.get(image_url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    # Image-optimization proxies (Next.js /_next/image, Cloudinary, imgix,
    # ...) serve the same underlying photo at many URLs (different sizes/
    # query params) — dedupe by content hash rather than URL so those don't
    # get treated as distinct images.
    content_hash = hashlib.sha256(resp.content).hexdigest()
    if content_hash in seen_hashes:
        return None
    seen_hashes.add(content_hash)

    ext = _sniff_extension(resp.content) or Path(urlparse.urlparse(image_url).path).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        ext = ".jpg"
    local_path = output_dir / f"scraped_{index:04d}{ext}"
    local_path.write_bytes(resp.content)
    return local_path


def _sniff_extension(content: bytes) -> str | None:
    """Determine the real file extension from content, not the URL — image
    optimization proxies (Next.js /_next/image, etc.) often have no usable
    extension in the path at all, and whatever's there can be misleading
    (e.g. a .jpg-looking URL actually serving a palette-mode PNG), which
    downstream tools that trust the extension (like Pillow's save()) choke
    on.
    """
    try:
        with Image.open(io.BytesIO(content)) as img:
            fmt = (img.format or "").lower()
    except Exception:
        return None
    return {"jpeg": ".jpg", "png": ".png", "webp": ".webp", "gif": ".gif"}.get(fmt)


def scrape_images(
    base_url: str,
    output_dir: Path,
    max_pages: int = 20,
    max_images: int = 500,
) -> list[ScrapedImage]:
    """Crawl same-domain pages from base_url and download every discovered
    image, honoring robots.txt for both pages and image URLs.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    domain = urlparse.urlparse(base_url).netloc
    robots = _load_robots(base_url, session)

    seen_pages = {base_url}
    queue = [base_url]
    seen_image_urls: set[str] = set()
    seen_hashes: set[str] = set()
    results: list[ScrapedImage] = []

    while queue and len(seen_pages) <= max_pages and len(results) < max_images:
        page_url = queue.pop(0)
        if not robots.can_fetch(USER_AGENT, page_url):
            continue
        try:
            resp = session.get(page_url, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
        except requests.RequestException:
            continue
        time.sleep(REQUEST_DELAY_SECONDS)

        html = resp.text
        for image_url in _extract_image_urls(html, page_url):
            if len(results) >= max_images or image_url in seen_image_urls:
                continue
            seen_image_urls.add(image_url)
            if not robots.can_fetch(USER_AGENT, image_url):
                continue
            local_path = _download_image(session, image_url, output_dir, len(results), seen_hashes)
            time.sleep(REQUEST_DELAY_SECONDS)
            if local_path:
                results.append(ScrapedImage(image_url=image_url, page_url=page_url, local_path=local_path))

        for link in _extract_page_links(html, page_url, domain):
            if link not in seen_pages and len(seen_pages) < max_pages:
                seen_pages.add(link)
                queue.append(link)

    return results
