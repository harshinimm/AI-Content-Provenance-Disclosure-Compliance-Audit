"""SynthID watermark check.

There is no public API for SynthID verification as of this writing — Google
exposes it only through the Gemini app, Chrome, and Search's "About this
image" / AI-detection surfaces. This module records a manual-check result
rather than pretending to automate it.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SynthIDResult:
    detected: bool | None  # None = not yet manually checked
    method: str
    notes: str = ""


def check(image_path: str, manual_result: bool | None = None) -> SynthIDResult:
    """Record a SynthID check result.

    Pass `manual_result` (True/False) once you've verified the image through
    the Gemini app / Chrome / Search. Leaving it unset marks the check as
    pending so it isn't silently scored as "not watermarked".
    """
    if manual_result is None:
        return SynthIDResult(
            detected=None,
            method="manual_pending",
            notes="Run image through Gemini app / Chrome / Google Search AI-detection and record result.",
        )
    return SynthIDResult(detected=manual_result, method="manual")
