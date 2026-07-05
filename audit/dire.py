"""DIRE (DIffusion Reconstruction Error) scoring.

Wraps a pretrained DIRE checkpoint/classifier from ZhendongWang6/DIRE. This
module doesn't vendor the model — set DIRE_SCRIPT and DIRE_MODEL_PATH to
point at a cloned checkout, or pass them explicitly to `check()`.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DIREResult:
    reconstruction_error: float | None
    is_generated: bool | None
    error: str | None = None


def check(
    image_path: str | Path,
    script_path: str | None = None,
    model_path: str | None = None,
) -> DIREResult:
    """Run DIRE inference on a single image.

    Expects `script_path` to be a Python script (from a cloned DIRE repo)
    that accepts `--image`, `--model`, and prints a JSON object like
    `{"dire_score": 0.0123, "is_generated": true}` to stdout. Wire up the
    exact invocation once you've cloned github.com/ZhendongWang6/DIRE and
    have a checkpoint.
    """
    script_path = script_path or os.environ.get("DIRE_SCRIPT")
    model_path = model_path or os.environ.get("DIRE_MODEL_PATH")

    if not script_path or not model_path:
        return DIREResult(
            reconstruction_error=None,
            is_generated=None,
            error="DIRE not configured — set DIRE_SCRIPT and DIRE_MODEL_PATH env vars.",
        )

    proc = subprocess.run(
        ["python", script_path, "--image", str(image_path), "--model", model_path],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return DIREResult(reconstruction_error=None, is_generated=None, error=proc.stderr.strip())

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return DIREResult(reconstruction_error=None, is_generated=None, error=f"unparseable output: {exc}")

    return DIREResult(
        reconstruction_error=result.get("dire_score"),
        is_generated=result.get("is_generated"),
    )
