# AI Content Provenance & Disclosure Compliance Audit — Project Guide

## 1. Objective

Scrape a company's site, triage which images are likely AI-generated at
scale (so only that flagged subset gets the expensive checks), then test
whether those images carry legally-required disclosure signals (C2PA
metadata, SynthID watermark) and whether those signals survive real-world
transformations. Score the results against EU AI Act Article 50(2) and
California SB 942, and flag related IP/copyright exposure.

**Deliverable:** a CLI tool + web app (`web/`, backed by `server.py`) that
runs this against any company's site, with a self-audit framing —
"check your own site before a regulator does," not a tool for calling out
other companies. A public write-up is optional, not required — the working
tool is the deliverable now, not a blog post (see §9).

---

## 2. Legal basis (what you're testing against)

### EU AI Act — Article 50(2)
- Providers of AI systems generating synthetic image/audio/video/text content must ensure outputs are marked in a **machine-readable format and detectable as artificially generated**.
- The marking must be **effective, robust, reliable, and interoperable**, "as far as technically feasible."
- Persistence matters: providers must prevent deliberate removal or alteration of markings — not just apply them once.
- Effective **August 2, 2026** (existing systems on the market get until Dec 2, 2026 under the AI Omnibus transition).
- C2PA + SynthID are the reference technologies named in the draft Code of Practice, not the statute itself.
- Penalties: up to €15M or 3% global turnover.

### California SB 942 (AI Transparency Act)
- Applies only to **image, video, or audio** — not text.
- Only binds "Covered Providers": generative AI systems with **>1,000,000 monthly CA users/visitors**.
- Requires **latent (hidden) disclosure** conveying provenance info, and it must be **"permanent or extraordinarily difficult to remove."**
- Visible/manifest disclosure is optional but must meet a legibility standard if offered.
- Effective **January 1, 2026** (already live).
- Penalties: up to $5,000/day/violation, AG/city/county enforcement only.

**Not legal advice** — verdicts are an automated, best-effort reading of
these statutes against signals this tool can detect. See §6's caveats and
the web app's Info page before anyone acts on output.

---

## 3. Data sources

| Layer | Source | Why |
|---|---|---|
| Primary audit target | A real (or your own) company's site, pulled via `audit.py --url` / the web app's Overview form ([`audit/scraper.py`](audit/scraper.py)) | The actual subject of the audit — only the triage-flagged subset gets C2PA/SynthID/transform checks |
| Triage classifier ground truth | 5 known-real photos (Picsum/Unsplash) + 3 freshly-generated known-AI images (Pollinations) — independently sourced, not the tool's own opinions | Used once to benchmark and pick the current DIRE-gate classifier (see [`audit/dire.py`](audit/dire.py) and README) — not something you need to re-run per audit |

DiffusionForensics / the official DIRE paper method are **no longer part of
this project** — see §4.3.

---

## 4. Tooling setup

1. **c2patool** — CLI tool from the C2PA org (now `contentauth/c2pa-rs`'s
   `cli/` crate, the standalone repo is archived), reads/verifies C2PA
   manifests. Works out of the box once `C2PATOOL_PATH` is set — see README.
2. **SynthID verification** — Google's official [SynthID Detector](https://blog.google/innovation-and-ai/products/google-synthid-ai-content-detector/)
   portal exists but is a one-file-at-a-time web upload, currently waitlisted
   to journalists/researchers, with no public API — can't be scripted.
   Instead, script this layer with
   [`gpt-image-synthid-detector`](https://github.com/newideas99/gpt-image-synthid-detector),
   a pip-installable open-source CNN classifier (pretrained weights included)
   that self-reports ~97% validation accuracy against OpenAI's public
   verifier. Caveats: it's trained/validated on **GPT-Image-2** only, so
   accuracy on Google's own Imagen/Veo/Gemini-native images is unproven; the
   97% figure is self-reported with minimal community validation (3 stars,
   1 fork, single commit); and it's licensed **PolyForm Noncommercial**
   (fine for this audit, blocks a future commercial product). Label the
   SynthID column in output as a **"community-detector estimate
   (unofficial)"**, not equivalent to Google's own verification.
3. **DIRE triage gate — the official method is abandoned, not pursuing it.**
   `ZhendongWang6/DIRE`'s real pipeline needs a GPU/MPI setup and a
   pretrained checkpoint only distributed via Baidu/RecDrive (both
   unreachable from here, no accessible mirror exists anywhere). Instead,
   [`audit/dire.py`](audit/dire.py) runs a 2-model classifier ensemble —
   `Ateeqq/ai-vs-human-image-detector` AND `prithivMLmods/Deep-Fake-Detector-v2-Model`,
   both must agree for a flag. Chosen after benchmarking 4 candidates
   against the ground-truth set in §3 (full comparison table in README);
   no single-model swap was strictly better, each traded one failure mode
   for a worse one. Works out of the box, CPU-only, no setup. A Colab
   notebook (`colab/dire_batch.ipynb`) exists for running the *real* DIRE
   method if you ever get the checkpoint working, but it's unverified and
   not a priority — the local ensemble is the supported path.
4. **Pillow (PIL)** — Python image library for the transformation battery: screenshot simulation, recompress (JPEG quality reduction), crop, resize.
5. **The web app** ([`server.py`](server.py) + [`web/`](web/)) — a FastAPI
   backend wrapping the same `audit/` pipeline as the CLI, plus a React
   frontend (Overview/Results/Info). Deploy split: frontend as a static
   Vercel build, backend needs a host with persistent processes/disk
   (Railway, etc.) — see README's Deploying section.

---

## 5. Pipeline

**Step 0 — Bulk collection** ([`audit/scraper.py`](audit/scraper.py))
1. Scrape all images from the target site (`audit.py --url`, or the web app's Overview form), same-domain, robots.txt-respecting
2. Drop anything under 150px on either dimension (icons/favicons/partner logos, not content photos) and anything Pillow can't identify as a real raster image (SVGs, HTML error pages) — both found as real bugs while testing against live sites, not hypothetical

**Step 1 — Triage gate** ([`audit/pipeline.py`](audit/pipeline.py)`:run_image`)
3. Run the 2-model ensemble on every scraped image → log the AND-gated score + binary classification
4. If not flagged as AI-generated, **skip it** — no C2PA/SynthID/transform checks run, verdict is recorded as "Not Applicable." If the classifier isn't configured or errors, this fails open (full checks still run) rather than silently skipping everything.

**Step 2 — Baseline checks (pre-transformation), flagged subset only**
5. Run c2patool → log: manifest present (Y/N), full contents (including rights/copyright/authorship fields for the IP layer)
6. Run SynthID check → log: watermark detected (Y/N)

**Step 3 — Apply transformation battery**
7. Screenshot (simulate via re-render + recapture)
8. Recompress (reduce JPEG quality)
9. Crop (remove a border region)
10. Resize (scale down then back up)

**Step 4 — Re-run checks (post-transformation)**
11. Repeat steps 5–6 on each transformed variant
12. Re-run the triage classifier post-transformation too, logged as a secondary signal (does the detector's own confidence survive editing) — doesn't change the legal verdict, which is driven by C2PA/SynthID
13. Log all results against the same schema as Step 2

---

## 6. Legal verdict encoding (this is where you translate law into rules)

For each image, compute **two independent verdicts** — they are not the same threshold:

**Article 50(2) verdict:**
- Marked AND survives ≥ recompress/crop/resize → `Likely Compliant`
- Marked pre-transformation, gone post-transformation → `Marked but not Robust → Gap`
- Not marked at all → `Non-Compliant`
- Note separately if the triage classifier still flags it as AI-generated post-strip — arguably doesn't satisfy "machine-readable," even though it's technically detectable. Flag as a nuance, not a pass.

**SB 942 verdict:**
- Same present/survives logic, but apply the stricter "extraordinarily difficult to remove" bar — an image can pass the EU test and fail the CA one.

**IP flag:**
- Copyright claim on the page/site + image likely lacks human authorship → `Copyrightability Risk`
- C2PA manifest carried rights/licensing fields pre-transformation but not post → `Lost Attribution Chain`

Each Non-Compliant/Gap verdict in the web app now also shows a concrete
remediation tip (`remediationFor()` in `web/src/lib/types.ts`) — a
self-audit tool needs to answer "now what," not just flag a problem.

---

## 7. Tool packaging

Two interfaces over the same pipeline:

```bash
# CLI
python audit.py ./test_images/
python audit.py --url https://example-company.com

# Web app (see README for full setup)
uvicorn server:app --port 8000   # backend
cd web && npm run dev             # frontend, http://localhost:5173
```

CSV/markdown output columns:

`source | tool | C2PA pre/post | SynthID pre/post | DIRE pre/post | Article 50 verdict | SB 942 verdict | IP flag`

---

## 8. Status / order of operations

Done:
1. ~~Pull DiffusionForensics, set up official DIRE~~ — abandoned, see §4.3
2. Benchmarked the triage classifier against independently-sourced ground truth, picked the AND-gated ensemble
3. Scraper built and hardened (icon filtering, SVG/unrecognized-content rejection, dedup)
4. C2PA + SynthID wired up and working
5. Transform battery + verdict logic built
6. CLI built
7. Web app built (Overview self-audit form, Results with live/example modes + image thumbnails + remediation tips, Info page)
8. Tested end-to-end against real companies: elevenlabs.io, heygen.com, jasper.ai, synthesia.io, framer.com
9. Backend hardened for public reachability (SSRF guard, rate limiting) and made deployable (Dockerfile)

Open:
- Frontend deploy to Vercel (in progress — framework-preset/build config issues)
- Backend hosting decision (Railway attempt paused — currently local-only, meaning the deployed frontend's live-audit form won't work for anyone but you)
- Source-URL traceability gap — no way to click through from a result card to where an image actually came from on the live site (flagged, not yet built)
- Optional: a public write-up (§9) — not required for the project to be "done"

---

## 9. Write-up structure (optional — see §1)

If you do decide to write something up:

1. Hook: the SynthID-stripping tool exists; regulation assumes marks survive — do they?
2. Plain-English breakdown: what Article 50 / SB 942 actually require vs. common assumptions
3. Methodology: the pipeline above, stated plainly
4. Results table
5. Key finding: which signals survive, which don't
6. Caveats: sample size, the triage classifier's documented precision/recall tradeoff, SynthID check is a community-detector estimate validated only on GPT-Image-2 (not Google's own generators), not Google's official verifier
7. What this means for companies deploying AI content today

Given the self-audit pivot, naming specific companies in a public piece
carries real legal exposure (defamation/tortious interference risk if a
named company disputes a finding) that a private/internal summary
wouldn't — worth deciding deliberately, not by default.
