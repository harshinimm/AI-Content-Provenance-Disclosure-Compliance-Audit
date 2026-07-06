# AI Content Provenance & Disclosure Compliance Audit — Project Guide

## 1. Objective

Scrape a company's site, use DIRE to triage which images are likely AI-generated at scale (so only that flagged subset gets the expensive checks), then test whether those images carry legally-required disclosure signals (C2PA metadata, SynthID watermark) and whether those signals survive real-world transformations. Score the results against EU AI Act Article 50(2) and California SB 942, and flag related IP/copyright exposure.

**Deliverable:** a scored comparison table, a small CLI tool/repo, and a Substack-ready write-up.

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

---

## 3. Data sources (split by layer — don't use one dataset for everything)

| Layer | Source | Sample size | Why |
|---|---|---|---|
| Primary audit target | A real company's site, pulled via `audit.py --url` ([`audit/scraper.py`](audit/scraper.py)) | Hundreds, unbounded | The actual subject of the audit — only the DIRE-flagged subset gets C2PA/SynthID/transform checks |
| DIRE training/validation | **DiffusionForensics** benchmark dataset (public, 8 diffusion models, from the DIRE paper's GitHub repo) | Hundreds+ per model | Needs volume for a real statistical distribution; validates DIRE before trusting it on scraped, real-world-style images |
| Manual spot-check / ground truth | Images **you generate** across 2–3 tools (e.g. Imagen/Gemini, DALL-E, Stable Diffusion) | 5–10 per tool | Known-positive cases to sanity-check DIRE's precision on production-style content, and to exercise the C2PA/SynthID layers (freshly-generated images carry live provenance metadata/watermarks that scraped images may have already lost) |

Include **Stable Diffusion** as one of your 2–3 self-generation tools if possible — it's open, so it gives you the most accurate same-model DIRE comparison alongside the cross-model tests on DALL-E/Imagen.

---

## 4. Tooling setup

1. **c2patool** — CLI tool from the C2PA org, reads/verifies C2PA manifests. Install and confirm it runs on a sample image before touching your real set.
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
3. **DIRE** — pretrained diffusion model + reconstruction error pipeline, from `ZhendongWang6/DIRE` on GitHub. Reuses the DiffusionForensics dataset for training/validation of the binary classifier.
4. **Pillow (PIL)** — Python image library for the transformation battery: screenshot simulation, recompress (JPEG quality reduction), crop, resize.

---

## 5. Pipeline

**Step 0 — Bulk collection** ([`audit/scraper.py`](audit/scraper.py))
1. Scrape all images from the target company's site (`audit.py --url`), same-domain, robots.txt-respecting
2. (Optional) spot-check DIRE's accuracy on the self-generated ground-truth set first, so you know how much to trust Step 1 on real-world content

**Step 1 — DIRE triage gate** ([`audit/pipeline.py`](audit/pipeline.py)`:run_image`)
3. Run DIRE on every scraped image → log reconstruction error + binary classification
4. If DIRE classifies an image as real (`is_generated is False`), **skip it** — no C2PA/SynthID/transform checks run, verdict is recorded as "Not Applicable." If DIRE isn't configured or errors, this fails open (full checks still run) rather than silently skipping everything.

**Step 2 — Baseline checks (pre-transformation), DIRE-flagged subset only**
5. Run c2patool → log: manifest present (Y/N), full contents (including rights/copyright/authorship fields for the IP layer)
6. Run SynthID check → log: watermark detected (Y/N)

**Step 3 — Apply transformation battery**
7. Screenshot (simulate via re-render + recapture)
8. Recompress (reduce JPEG quality)
9. Crop (remove a border region)
10. Resize (scale down then back up)

**Step 4 — Re-run checks (post-transformation)**
11. Repeat steps 5–6 on each transformed variant
12. Optionally re-run DIRE post-transformation too — the paper reports it holds up under blur/compression, a good confirmation to log
13. Log all results against the same schema as Step 2

---

## 6. Legal verdict encoding (this is where you translate law into rules)

For each image, compute **two independent verdicts** — they are not the same threshold:

**Article 50(2) verdict:**
- Marked AND survives ≥ recompress/crop/resize → `Likely Compliant`
- Marked pre-transformation, gone post-transformation → `Marked but not Robust → Gap`
- Not marked at all → `Non-Compliant`
- Note separately if DIRE still flags it as AI-generated post-strip — arguably doesn't satisfy "machine-readable," even though it's technically detectable. Flag as a nuance, not a pass.

**SB 942 verdict:**
- Same present/survives logic, but apply the stricter "extraordinarily difficult to remove" bar — an image can pass the EU test and fail the CA one.

**IP flag:**
- Copyright claim on the page/site + image likely lacks human authorship → `Copyrightability Risk`
- C2PA manifest carried rights/licensing fields pre-transformation but not post → `Lost Attribution Chain`

---

## 7. Tool packaging

Wrap steps 0–4 into a single CLI:

```
python audit.py ./test_images/
python audit.py --url https://example-company.com
```

Should output one CSV/markdown table with columns:

`source | tool | C2PA pre/post | SynthID pre/post | DIRE pre/post | Article 50 verdict | SB 942 verdict | IP flag`

This CLI is your "optional script/repo as evidence of the work."

---

## 8. Order of operations

1. Pull the DiffusionForensics dataset and set up DIRE
2. Generate 5–10 self-made images across 2–3 tools — spot-check DIRE's real-world accuracy, and exercise C2PA/SynthID as known-positive cases
3. Pick a target company (site with visible AI imagery, ideally >1M monthly CA users, ideally makes a public AI-transparency claim)
4. Run `audit.py --url` against the target site — scraper pulls images, DIRE triage gate (done) filters to the flagged subset
5. Set up c2patool and `gpt-image-synthid-detector` so the flagged subset gets real checks instead of placeholders
6. Run the full battery (transform + re-check) on the flagged subset
7. Apply legal verdict + IP flag logic, generate the scored table
8. Write the Substack piece: law vs. technical reality, with DIRE's known robustness to blur/compression as the central finding, and the triage gate as the scalability angle

---

## 9. Write-up structure (suggested)

1. Hook: the SynthID-stripping tool exists; regulation assumes marks survive — do they?
2. Plain-English breakdown: what Article 50 / SB 942 actually require vs. common assumptions
3. Methodology: the pipeline above, stated plainly
4. Results table
5. Key finding: which signals survive, which don't, and what still works even after they're gone (DIRE)
6. Caveats: sample size asymmetry, cross-model DIRE limitations, SynthID check is a community-detector estimate validated only on GPT-Image-2 (not Google's own generators), not Google's official verifier
7. What this means for companies deploying AI content today
