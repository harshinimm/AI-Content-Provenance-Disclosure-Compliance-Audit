"""SynthID watermark check via a community-trained detector.

Google's official SynthID Detector portal has no public API — it's a
one-file-at-a-time web upload, currently waitlisted to journalists/
researchers (see README). So this wraps `gpt-image-synthid-detector`
(github.com/newideas99/gpt-image-synthid-detector), an open-source CNN
ensemble trained to recognize GPT-Image-2's SynthID watermark, run the
same way `dire.py` wraps a cloned external checkout.

This is NOT Google's own verification. Every result carries `method` so
callers can label it a "community-detector estimate (unofficial)" rather
than presenting it as equivalent to Google's verifier. Caveats: trained/
validated on GPT-Image-2 only, so accuracy on Google's own Imagen/Veo/
Gemini-native images is unproven; the accuracy figure is self-reported
with minimal independent validation (3 stars, 1 fork, single commit);
licensed PolyForm Noncommercial (fine for this audit, blocks commercial
reuse).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

METHOD_UNOFFICIAL = "community-detector estimate (unofficial, GPT-Image-2-trained)"
METHOD_MANUAL = "manual override"
METHOD_UNCONFIGURED = "not configured"

_ENSEMBLE_RE = re.compile(r"ensemble P\(watermarked\)\s*=\s*([\d.]+)")


@dataclass
class SynthIDResult:
    detected: bool | None  # None = not checked (unconfigured, or detector error)
    method: str
    score: float | None = None  # ensemble P(watermarked), 0-1
    notes: str = ""


def check(
    image_path: str | Path,
    manual_override: bool | None = None,
    repo_path: str | None = None,
) -> SynthIDResult:
    """Run the community SynthID detector ensemble against a single image.

    Pass `manual_override` to record a result verified another way (e.g.
    Google's official SynthID Detector portal, once you have waitlist
    access) instead of the automated estimate — takes precedence when set.
    """
    if manual_override is not None:
        return SynthIDResult(detected=manual_override, method=METHOD_MANUAL)

    repo_path = repo_path or os.environ.get("SYNTHID_DETECTOR_REPO")
    if not repo_path:
        return SynthIDResult(
            detected=None,
            method=METHOD_UNCONFIGURED,
            notes="SYNTHID_DETECTOR_REPO not set — clone "
            "github.com/newideas99/gpt-image-synthid-detector and set it, "
            "or pass manual_override.",
        )

    repo = Path(repo_path)
    detect_script = repo / "detect.py"
    if not detect_script.exists():
        return SynthIDResult(
            detected=None,
            method=METHOD_UNCONFIGURED,
            notes=f"detect.py not found at {detect_script}",
        )

    proc = subprocess.run(
        # sys.executable, not "python" — bare "python" can resolve to a
        # different interpreter than the one actually running this process
        # and silently lack torch/torchvision, failing opaquely downstream.
        # image_path is resolved to absolute first since cwd is pinned to
        # the detector repo below (a relative path would resolve against
        # the wrong directory otherwise).
        [sys.executable, str(detect_script), str(Path(image_path).resolve())],
        cwd=repo,  # detect.py resolves weights/ relative to cwd, not the script's location
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return SynthIDResult(detected=None, method=METHOD_UNCONFIGURED, notes=proc.stderr.strip())

    match = _ENSEMBLE_RE.search(proc.stdout)
    if not match:
        return SynthIDResult(
            detected=None,
            method=METHOD_UNCONFIGURED,
            notes=f"unparseable output: {proc.stdout.strip()[:200]}",
        )

    score = float(match.group(1))
    return SynthIDResult(detected=score > 0.5, method=METHOD_UNOFFICIAL, score=score)
