# AI Content Provenance & Disclosure Compliance Audit

Scans a company's site for AI-generated images, checks whether they carry
legally-required disclosure signals (C2PA metadata, SynthID watermark),
tests whether those signals survive real-world edits (screenshot, recompress,
crop, resize), and scores the result against **EU AI Act Article 50(2)** and
**California SB 942**. See [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) for the
full legal/methodology writeup.

## Quick start

```bash
pip install -r requirements.txt
python audit.py --url https://example-company.com
# or, for your own local images (one subfolder per generation tool):
python audit.py ./test_images/
```

This writes `output/results.csv` and `output/results.md` with columns:

`source | tool | C2PA pre/post | SynthID pre/post | DIRE pre/post | Article 50 verdict | SB 942 verdict | IP flag`

Notes:
- `--url` takes `--max-pages` (default 20) and `--max-images` (default 500);
  it's a static-HTML crawl only (no JS-rendered images), and saves a
  `manifest.csv` of source URLs alongside the downloaded images.
- Local-folder mode expects one subfolder per generation tool, e.g.
  `test_images/dalle/img1.png`, `test_images/imagen/img1.png`.

**DIRE triage works out of the box** — `pip install -r requirements.txt`
gets you a real (if practical-substitute) DIRE gate with no extra setup, no
GPU, no external tool. C2PA and SynthID checks fail safely (recorded as
`None`, not scored) until you set those two up below.

## External tools

Two checks shell out to a separate tool you need to set up; DIRE now works
by default.

| Tool | What it checks | Setup |
|---|---|---|
| [DIRE](#dire) | Is this image AI-generated at all (the triage gate) | None — works out of the box |
| [c2patool](#c2patool) | C2PA manifest present/survives | `C2PATOOL_PATH` |
| [gpt-image-synthid-detector](#synthid-detector) | SynthID watermark present/survives (unofficial estimate) | `SYNTHID_DETECTOR_REPO` |

### c2patool

The original repo is archived; it now ships from `contentauth/c2pa-rs`.

```bash
# 1. Download from https://github.com/contentauth/c2pa-rs/releases?q=c2patool
#    (Windows: c2patool-vX.Y.Z-x86_64-pc-windows-msvc.zip) and extract it
# 2. Point at it:
export C2PATOOL_PATH=/path/to/c2patool.exe
# 3. Verify:
c2patool -h
```

### DIRE

The paper's real method (ICCV 2023) needs two GPU/MPI-bound stages, and its
pretrained checkpoint only exists on Baidu/RecDrive — both often unreachable
outside China (we hit this directly: neither loaded). No accessible mirror
exists anywhere (checked HuggingFace, GitHub).

**Default path — works with no setup at all:** `dire.py` runs a 2-model
ensemble instead —
[`Ateeqq/ai-vs-human-image-detector`](https://huggingface.co/Ateeqq/ai-vs-human-image-detector)
AND
[`prithivMLmods/Deep-Fake-Detector-v2-Model`](https://huggingface.co/prithivMLmods/Deep-Fake-Detector-v2-Model),
both must independently call an image AI-generated for it to flag. Neither
is the paper's diffusion-reconstruction-error technique — honestly labeled
in output/notes as a *"practical substitute for DIRE."* Weights download
automatically on first use (~400-500MB each, one-time, over normal HTTPS —
no Baidu involved).

**Why an ensemble, and why AND-gated:** the single-model version had a real
false-positive problem — real photos confidently (>99%) called
AI-generated. Benchmarked against 5 known-real photos (Picsum/Unsplash) and
3 freshly-generated known-AI images (Pollinations) before picking a fix:

| Model | Real-photo accuracy | AI-image recall |
|---|---|---|
| Ateeqq alone | 3/5 | 3/3 |
| dima806/ai_vs_real_image_detection | 0/5 (called *everything* fake) | 3/3 |
| prithivMLmods alone | 1/5 (mostly ~55% coin-flip) | 1/3 |
| umm-maybe/AI-image-detector | 5/5 | 0/3 (2022-era, blind to modern generators) |
| **Ateeqq AND prithivMLmods (current)** | **4/5** | **2/3** |

No single swap was strictly better — each traded the false-positive problem
for a worse failure mode. The AND-gate is a genuine precision/recall
tradeoff, not a free win: it cut false positives (2/5 → 1/5 wrong) at a
real recall cost (3/3 → 2/3 known-AI images detected). Treat this as a
documented limitation, not a solved problem — general AI-image detection
genuinely struggles to generalize across real-world photo diversity and
generators simultaneously right now.

**If you do get the real DIRE checkpoint working** (e.g. from within China,
or a VPN), `colab/dire_batch.ipynb` runs the actual paper method on Colab's
free GPU and produces a `dire_results.csv` — set `DIRE_RESULTS_CSV` and
`dire.py` prefers that over the local classifier, looking up each image by
filename. A live local path (`DIRE_SCRIPT`/`DIRE_MODEL_PATH`) also exists
for a future GPU machine, but is unverified — the real DIRE repo doesn't
expose a single JSON-emitting script the way that path assumes.

### SynthID detector

Google's own [SynthID Detector](https://blog.google/innovation-and-ai/products/google-synthid-ai-content-detector/)
has no public API (waitlisted web upload only), so this uses a third-party
open-source classifier instead.

```bash
git clone https://github.com/newideas99/gpt-image-synthid-detector
cd gpt-image-synthid-detector && pip install -r requirements.txt && cd ..
export SYNTHID_DETECTOR_REPO=/path/to/gpt-image-synthid-detector
```

**This is not Google's own verification** — results are labeled
`(unofficial)` in the output. Why: the detector is trained only on
GPT-Image-2, so accuracy on Google's own Imagen/Veo/Gemini images is
unproven; its self-reported ~97% accuracy has minimal independent
validation; and it's licensed PolyForm Noncommercial (fine for this
project, blocks commercial reuse). You can bypass it with a manually
verified result instead: `synthid.check(path, manual_override=True/False)`.

## Web UI

A local web frontend (`web/`, Vite + React) lets you enter a URL in the
browser and watch an audit run live, with image thumbnails per result —
instead of using the CLI directly.

```bash
# terminal 1 — the API server (wraps the same audit/ pipeline as the CLI)
pip install -r requirements.txt
uvicorn server:app --port 8000

# terminal 2 — the frontend
cd web
npm install
npm run dev
```

Open http://localhost:5173 — Overview has the URL input, Results shows
per-image output (live for a real run, or a bundled example from
elevenlabs.io if you just browse to `/results` directly), Info has the
legal/methodology writeup.

**Local-only, not for public deployment** — `server.py` has no auth or
rate limiting and shells out to scrape whatever URL it's given (an
SSRF-shaped risk if exposed). Keep it bound to localhost.

## Making env vars persistent

The exports above only last for one terminal session. To make them
permanent, add them to your PowerShell profile (`$PROFILE`) — ask and I'll
set it up.

## Troubleshooting: SSL errors on Windows

If scraping or `git push`/`git clone` fails with a certificate error, it's
almost always antivirus HTTPS-scanning injecting a root cert your tools
don't trust yet — not a real network block.

```bash
pip install pip-system-certs          # fixes Python/requests (the scraper)
git config http.sslBackend schannel   # fixes git, scoped to one repo
```

## Layout

```
audit/
  scraper.py     # crawls a site for images (--url), robots.txt-respecting
  pipeline.py    # per-image orchestration: DIRE triage gate -> checks -> transform battery -> re-check
  c2pa.py        # c2patool wrapper
  synthid.py     # SynthID detector wrapper (unofficial) + manual_override
  dire.py        # AND-gated 2-model classifier ensemble by default (practical substitute); DIRE_RESULTS_CSV/DIRE_SCRIPT as alternates
  transforms.py  # screenshot/recompress/crop/resize battery
  verdict.py     # Article 50(2) / SB 942 / IP-flag legal encoding
audit.py         # CLI entrypoint
server.py        # local API server wrapping audit/ for the web frontend (see Web UI)
web/             # Vite + React frontend: URL input, live results with image thumbnails, methodology page
test_images/     # your self-generated images, one subfolder per tool (gitignored)
data/diffusion_forensics/  # DiffusionForensics dataset for DIRE (gitignored)
```

## Status

- **Working out of the box:** scraper, DIRE triage gate (local classifier, no setup), transform battery, legal verdict logic
- **Working, needs setup:** C2PA checks (`C2PATOOL_PATH`), SynthID checks (`SYNTHID_DETECTOR_REPO`, unofficial)
- **Working, optional:** the real DIRE method via `colab/dire_batch.ipynb` + `DIRE_RESULTS_CSV`, if you can reach Baidu/RecDrive
- **Unverified:** the live local DIRE path (`DIRE_SCRIPT`/`DIRE_MODEL_PATH`) — untested, needs a GPU machine to confirm
- **Not started:** picking a target company to actually audit
