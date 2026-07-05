# AI Content Provenance & Disclosure Compliance Audit

Tests whether AI-generated images carry legally-required disclosure signals
(C2PA metadata, SynthID watermark), whether those signals survive real-world
transformations (screenshot, recompress, crop, resize), and whether a
statistical fingerprint (DIRE) remains detectable even when they don't.
Scores results against **EU AI Act Article 50(2)** and **California SB 942**,
and flags related IP/copyright exposure.

See [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) for the full methodology and legal
basis this tool encodes.

## Setup

```bash
pip install -r requirements.txt
```

External tools this pipeline shells out to (install separately):

- **c2patool** — reads/verifies C2PA manifests. https://github.com/contentauth/c2patool
  Verify it works: `c2patool path/to/sample.jpg`
- **DIRE** — diffusion reconstruction error classifier. Clone
  https://github.com/ZhendongWang6/DIRE, get a pretrained checkpoint, then set:
  ```bash
  export DIRE_SCRIPT=/path/to/DIRE/compute_dire.py
  export DIRE_MODEL_PATH=/path/to/checkpoint.pt
  ```
  Without these set, DIRE checks are skipped (recorded as `None`, not scored).
- **SynthID** — Google's official [SynthID Detector](https://blog.google/innovation-and-ai/products/google-synthid-ai-content-detector/)
  portal now exists, but it's a one-file-at-a-time web upload, currently
  gated to a journalist/researcher waitlist, with no public API — so it
  can't be scripted into this pipeline.
  Plan: switch `synthid.py` from the manual-check design to
  [`gpt-image-synthid-detector`](https://github.com/newideas99/gpt-image-synthid-detector),
  a pip-installable open-source CNN classifier with pretrained weights that
  self-reports ~97% validation accuracy against OpenAI's public verifier.
  Caveats to carry into the output:
  - It's trained/validated on **GPT-Image-2** (OpenAI's SynthID
    implementation) only — accuracy on Google's own Imagen/Veo/Gemini-native
    images is unproven, even though both now use the shared SynthID standard.
  - Minimal community validation (3 stars, 1 fork, single commit) — the 97%
    figure is self-reported, not independently vetted.
  - Licensed **PolyForm Noncommercial** — fine for this audit/Substack use,
    but blocks commercial use if this ever becomes a productized tool.
  Because of this, the SynthID column should be labeled in output as a
  **"community-detector estimate (unofficial)"** rather than presented as
  equivalent to Google's own verification, and rows for likely
  non-GPT-Image-2 sources should be flagged lower-confidence.

### Troubleshooting: SSL errors when scraping

If `--url` fails every page with SSL/certificate errors on Windows, it's
almost always antivirus HTTPS-scanning injecting a root cert that `certifi`'s
bundle doesn't trust — not a real network block. Fix by pulling in the
Windows trust store instead of disabling verification:

```bash
pip install pip-system-certs
```

## Usage

```bash
python audit.py ./test_images/
python audit.py --url https://example-company.com
```

Expects one subfolder per generation tool when using a local folder:

```
test_images/
  dalle/img1.png
  imagen/img1.png
  stable_diffusion/img1.png
```

With `--url`, Step 0 (bulk collection) crawls the site instead: same-domain
pages only, robots.txt-respecting, up to `--max-pages` (default 20) and
`--max-images` (default 500). Downloaded images and a `manifest.csv` (source
page + image URL per file) land in `<output-dir>/scraped/`. It's a
static-HTML crawl only — JS-rendered images and external CSS
background-images aren't picked up.

Writes `output/results.csv` and `output/results.md` with columns:

`source | tool | C2PA pre/post | SynthID pre/post | DIRE pre/post | Article 50 verdict | SB 942 verdict | IP flag`

## Layout

```
audit/
  scraper.py     # Step 0: same-domain image crawl + manifest, robots.txt-respecting
  c2pa.py        # c2patool wrapper, manifest + rights-field parsing
  synthid.py     # manual-check recorder today; migrating to
                 # gpt-image-synthid-detector for full automation (see Setup)
  dire.py        # pluggable wrapper around a cloned DIRE checkout
  transforms.py  # Pillow-based screenshot/recompress/crop/resize battery
  verdict.py     # Article 50(2) / SB 942 / IP-flag legal encoding
  pipeline.py    # per-image orchestration: baseline -> battery -> re-check
audit.py         # CLI entrypoint
test_images/     # your self-generated images, one subfolder per tool (gitignored)
data/diffusion_forensics/  # DiffusionForensics dataset for DIRE (gitignored)
```

## Status

Scaffold stage. `scraper.py`, `transforms.py`, and `verdict.py` are fully
implemented. `c2pa.py` and `dire.py` need their external tools
installed/configured per above before checks return real data. `synthid.py`
still uses the old manual-check design — next up is swapping it for
`gpt-image-synthid-detector` so the whole pipeline runs unattended (see
Setup notes above for caveats to carry into the output). Also still
pending: gating the pipeline on DIRE's triage verdict so scraped sites only
run the expensive C2PA/SynthID/transform checks on the DIRE-flagged subset,
per the project guide's Step 1 — right now every scraped image runs the
full pipeline regardless of DIRE's verdict.
