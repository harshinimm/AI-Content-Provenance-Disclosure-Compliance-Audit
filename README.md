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

- **c2patool** — reads/verifies C2PA manifests. The standalone repo is
  archived; it now lives in the `cli/` crate of
  [contentauth/c2pa-rs](https://github.com/contentauth/c2pa-rs). Download a
  prebuilt binary from the [releases page filtered for c2patool](https://github.com/contentauth/c2pa-rs/releases?q=c2patool)
  (Windows: `c2patool-vX.Y.Z-x86_64-pc-windows-msvc.zip`) and extract it
  anywhere. Either put `c2patool.exe` on PATH, or point at it directly
  (same env-var pattern as DIRE/SynthID below):
  ```bash
  export C2PATOOL_PATH=/path/to/c2patool.exe
  ```
  Verify it works: `c2patool -h`, then `c2patool path/to/sample.jpg`.
- **DIRE** — diffusion reconstruction error classifier. Clone
  https://github.com/ZhendongWang6/DIRE, get a pretrained checkpoint, then set:
  ```bash
  export DIRE_SCRIPT=/path/to/DIRE/compute_dire.py
  export DIRE_MODEL_PATH=/path/to/checkpoint.pt
  ```
  Without these set, DIRE checks are skipped (recorded as `None`, not scored).
- **SynthID** — Google's official [SynthID Detector](https://blog.google/innovation-and-ai/products/google-synthid-ai-content-detector/)
  portal exists but is a one-file-at-a-time web upload, currently gated to a
  journalist/researcher waitlist, with no public API — can't be scripted.
  Instead, `synthid.py` shells out to
  [`gpt-image-synthid-detector`](https://github.com/newideas99/gpt-image-synthid-detector),
  an open-source CNN ensemble (PyTorch; not pip-installable as a package —
  clone it and install its own `requirements.txt`, which pulls in
  `torch`/`torchvision`):
  ```bash
  git clone https://github.com/newideas99/gpt-image-synthid-detector
  cd gpt-image-synthid-detector && pip install -r requirements.txt && cd -
  export SYNTHID_DETECTOR_REPO=/path/to/gpt-image-synthid-detector
  ```
  Without `SYNTHID_DETECTOR_REPO` set, checks are recorded as `None` (not
  scored) — same fail-safe pattern as DIRE. You can also pass
  `manual_override=True/False` to `synthid.check()` to record a result
  verified another way (e.g. via the official portal, once you have
  waitlist access) instead of the automated estimate.

  Caveats carried into every output row (`synthid.py`'s `method` field,
  surfaced as `"(unofficial)"` in the CSV and as a note):
  - Trained/validated on **GPT-Image-2** (OpenAI's SynthID implementation)
    only — accuracy on Google's own Imagen/Veo/Gemini-native images is
    unproven, even though both now use the shared SynthID standard.
  - Minimal community validation (3 stars, 1 fork, single commit) — the 97%
    self-reported validation accuracy figure isn't independently vetted.
  - Licensed **PolyForm Noncommercial** — fine for this audit/Substack use,
    but blocks commercial use if this ever becomes a productized tool.
  Because of this, the SynthID columns are labeled `(unofficial)` rather
  than presented as equivalent to Google's own verification, and rows for
  likely non-GPT-Image-2 sources should be treated as lower-confidence.

### Troubleshooting: SSL errors on Windows

If `--url` fails every page with SSL/certificate errors, or `git push`
fails with "unable to get local issuer certificate," it's almost always
antivirus HTTPS-scanning injecting a root cert that the tool's bundled CA
store doesn't trust — not a real network block. Fix by pointing each tool at
the Windows trust store instead of disabling verification:

```bash
# for the scraper (Python/requests)
pip install pip-system-certs

# for git push/fetch over https, scoped to this repo
git config http.sslBackend schannel
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
  synthid.py     # gpt-image-synthid-detector wrapper (unofficial estimate) + manual_override escape hatch
  dire.py        # pluggable wrapper around a cloned DIRE checkout
  transforms.py  # Pillow-based screenshot/recompress/crop/resize battery
  verdict.py     # Article 50(2) / SB 942 / IP-flag legal encoding
  pipeline.py    # per-image orchestration: DIRE triage gate -> baseline -> battery -> re-check
audit.py         # CLI entrypoint
test_images/     # your self-generated images, one subfolder per tool (gitignored)
data/diffusion_forensics/  # DiffusionForensics dataset for DIRE (gitignored)
```

## Status

Scaffold stage. `scraper.py`, `transforms.py`, and `verdict.py` are fully
implemented. `pipeline.py` now gates on DIRE's triage verdict: images DIRE
classifies as real skip C2PA/SynthID/transform checks entirely (verdict
recorded as "Not Applicable"), and it fails open (runs full checks) if DIRE
errors or isn't configured, so `--url` won't silently report everything as
compliant before DIRE is wired up. `synthid.py` now automates checks via
`gpt-image-synthid-detector`, labeling results `(unofficial)` in the CSV per
the caveats above; `manual_override` remains available as an escape hatch.
`c2pa.py`, `dire.py`, and the SynthID detector still need their external
tools/checkpoints installed and env vars set (per Setup above) before checks
return real data instead of `None`.
