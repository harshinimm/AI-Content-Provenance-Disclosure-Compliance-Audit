"""CLI entrypoint for the AI Content Provenance & Disclosure Compliance Audit.

Usage:
    python audit.py ./test_images/
    python audit.py --url https://example-company.com

Expects test_images/ to contain one subfolder per generation tool, e.g.:
    test_images/dalle/img1.png
    test_images/imagen/img1.png
    test_images/stable_diffusion/img1.png

With --url, Step 0 (bulk collection) crawls the given site instead: same-domain
pages only, robots.txt-respecting, images saved under <output-dir>/scraped/
alongside a manifest.csv logging each image's source page and URL.

Writes output/results.csv and output/results.md.
"""
from __future__ import annotations

import urllib.parse as urlparse
from pathlib import Path

import click
import pandas as pd

from audit.pipeline import run_image
from audit.scraper import scrape_images
from audit.synthid import METHOD_UNOFFICIAL
from audit.transforms import BATTERY

VARIANT_SUFFIXES = tuple(f"_{name}" for name in BATTERY)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _fmt_synthid(detected: bool | None, method: str) -> str:
    if detected is None:
        return "N/A"
    suffix = " (unofficial)" if method == METHOD_UNOFFICIAL else ""
    return f"{detected}{suffix}"


def _is_source_image(path: Path) -> bool:
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    return not path.stem.endswith(VARIANT_SUFFIXES)


def _discover_images(root: Path) -> list[tuple[Path, str]]:
    """Return (path, tool) pairs, one per source image, tool inferred from
    the immediate parent folder name.
    """
    images = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and _is_source_image(path):
            tool = path.parent.name if path.parent != root else "unknown"
            images.append((path, tool))
    return images


@click.command()
@click.argument("image_dir", required=False, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--url", "site_url", default=None, help="Scrape images from this company site (Step 0) instead of a local folder.")
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("output"), help="Where to write results.")
@click.option("--max-pages", default=20, help="Max same-domain pages to crawl when using --url.")
@click.option("--max-images", default=500, help="Max images to download when using --url.")
def main(image_dir: Path | None, site_url: str | None, output_dir: Path, max_pages: int, max_images: int) -> None:
    if not image_dir and not site_url:
        raise click.UsageError("Provide either IMAGE_DIR or --url.")
    if image_dir and site_url:
        raise click.UsageError("Provide only one of IMAGE_DIR or --url, not both.")

    if site_url:
        scrape_dir = output_dir / "scraped"
        click.echo(f"Scraping {site_url} (max_pages={max_pages}, max_images={max_images})...")
        scraped = scrape_images(site_url, scrape_dir, max_pages=max_pages, max_images=max_images)
        if not scraped:
            click.echo("No images found (or all disallowed by robots.txt / unreachable).")
            return
        pd.DataFrame(
            [{"local_path": str(s.local_path), "image_url": s.image_url, "page_url": s.page_url} for s in scraped]
        ).to_csv(scrape_dir / "manifest.csv", index=False)
        click.echo(f"Downloaded {len(scraped)} images to {scrape_dir} (see manifest.csv for sources)")
        domain = urlparse.urlparse(site_url).netloc
        images = [(s.local_path, domain) for s in scraped]
    else:
        images = _discover_images(image_dir)

    if not images:
        click.echo(f"No source images found under {image_dir}")
        return

    rows = []
    for path, tool in images:
        click.echo(f"Auditing {path} (tool={tool})...")
        row = run_image(path, tool=tool)
        rows.append(row)
        for note in row.notes:
            click.echo(f"  note: {note}")

    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                "source": r.source,
                "tool": r.tool,
                "C2PA pre/post": f"{r.c2pa_pre}/{r.c2pa_post}",
                "SynthID pre/post": (
                    f"{_fmt_synthid(r.synthid_pre, r.synthid_pre_method)}/"
                    f"{_fmt_synthid(r.synthid_post, r.synthid_post_method)}"
                ),
                "DIRE pre/post": f"{r.dire_pre}/{r.dire_post}",
                "Article 50 verdict": r.article50_verdict,
                "SB 942 verdict": r.sb942_verdict,
                "IP flag": r.ip_flag,
            }
            for r in rows
        ]
    )

    csv_path = output_dir / "results.csv"
    md_path = output_dir / "results.md"
    df.to_csv(csv_path, index=False)
    md_path.write_text(df.to_markdown(index=False))

    click.echo(f"\nWrote {csv_path} and {md_path}")


if __name__ == "__main__":
    main()
