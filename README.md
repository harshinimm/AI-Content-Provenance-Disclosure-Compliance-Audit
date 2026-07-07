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

**You don't need any external tools installed to run this** — C2PA, DIRE,
and SynthID checks all fail safely (recorded as `None`, not scored) until
you set them up below. Wiring them up is what turns placeholder output into
a real audit.

## External tools

Three checks shell out to a separate tool. Each one is optional and
independent — set up as many as you need.

| Tool | What it checks | Set this env var |
|---|---|---|
| [c2patool](#c2patool) | C2PA manifest present/survives | `C2PATOOL_PATH` |
| [DIRE](#dire) | Is this image AI-generated at all (the triage gate) | `DIRE_SCRIPT`, `DIRE_MODEL_PATH` |
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

⚠️ **Known issue:** `audit/dire.py` expects a script that prints JSON
(`{"dire_score": ..., "is_generated": ...}`). The actual DIRE repo's
`demo.py -f <image> -m <model>` doesn't output that — this needs a fix
once someone has it cloned and can confirm the real output format. Don't
rely on DIRE results until this is resolved.

```bash
git clone https://github.com/ZhendongWang6/DIRE
# get a pretrained checkpoint from the README's BaiduDrive link (password: dire)
export DIRE_SCRIPT=/path/to/DIRE/demo.py      # will need adjusting, see above
export DIRE_MODEL_PATH=/path/to/checkpoint.pt
```

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
  dire.py        # DIRE wrapper (see Known Issue above)
  transforms.py  # screenshot/recompress/crop/resize battery
  verdict.py     # Article 50(2) / SB 942 / IP-flag legal encoding
audit.py         # CLI entrypoint
test_images/     # your self-generated images, one subfolder per tool (gitignored)
data/diffusion_forensics/  # DiffusionForensics dataset for DIRE (gitignored)
```

## Status

- **Working:** scraper, DIRE triage gate, C2PA checks, SynthID checks (unofficial), transform battery, legal verdict logic
- **Not working yet:** DIRE itself — see Known Issue above
- **Not started:** picking a target company to actually audit
