# AI Content Provenance & Disclosure Compliance Audit — Project Guide

## 1. Objective

Test whether AI-generated images carry legally-required disclosure signals (C2PA metadata, SynthID watermark), whether those signals survive real-world transformations, and whether a statistical fingerprint (DIRE) remains detectable even when they don't. Score the results against EU AI Act Article 50(2) and California SB 942, and flag related IP/copyright exposure.

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
| C2PA manifest check | Images **you generate** across 2–3 tools (e.g. Imagen/Gemini, DALL-E, Stable Diffusion) | 5–10 per tool | Only freshly-generated images carry live provenance metadata |
| SynthID watermark check | Same self-generated set | Same | Watermark is embedded at generation time |
| DIRE (diffusion reconstruction) | **DiffusionForensics** benchmark dataset (public, 8 diffusion models, from the DIRE paper's GitHub repo) | Hundreds+ per model | Needs volume for a real statistical distribution; no generation cost |

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

## 5. Pipeline — per image, run twice (pre- and post-transformation)

**Step A — Baseline checks (pre-transformation)**
1. Run c2patool → log: manifest present (Y/N), full contents (including rights/copyright/authorship fields for the IP layer)
2. Run SynthID check → log: watermark detected (Y/N)
3. Run DIRE → log: reconstruction error score, binary classification (real/generated)

**Step B — Apply transformation battery**
4. Screenshot (simulate via re-render + recapture)
5. Recompress (reduce JPEG quality)
6. Crop (remove a border region)
7. Resize (scale down then back up)

**Step C — Re-run baseline checks (post-transformation)**
8. Repeat steps 1–3 on each transformed variant
9. Log all results against the same schema as Step A

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

Wrap steps A–C into a single CLI:

```
python audit.py ./test_images/
```

Should output one CSV/markdown table with columns:

`source | tool | C2PA pre/post | SynthID pre/post | DIRE pre/post | Article 50 verdict | SB 942 verdict | IP flag`

This CLI is your "optional script/repo as evidence of the work."

---

## 8. Order of operations

1. Generate 5–10 self-made images across 2–3 tools (needed for C2PA/SynthID layers)
2. Pull the DiffusionForensics dataset (needed for DIRE layer) — can happen in parallel with step 1
3. Set up c2patool, `gpt-image-synthid-detector`, DIRE pipeline, Pillow transformation script
4. Build the CLI wrapper
5. Run the full battery on all images
6. Apply legal verdict + IP flag logic, generate the scored table
7. Write the Substack piece: law vs. technical reality, with DIRE's known robustness to blur/compression as the central finding

---

## 9. Write-up structure (suggested)

1. Hook: the SynthID-stripping tool exists; regulation assumes marks survive — do they?
2. Plain-English breakdown: what Article 50 / SB 942 actually require vs. common assumptions
3. Methodology: the pipeline above, stated plainly
4. Results table
5. Key finding: which signals survive, which don't, and what still works even after they're gone (DIRE)
6. Caveats: sample size asymmetry, cross-model DIRE limitations, SynthID check is a community-detector estimate validated only on GPT-Image-2 (not Google's own generators), not Google's official verifier
7. What this means for companies deploying AI content today
