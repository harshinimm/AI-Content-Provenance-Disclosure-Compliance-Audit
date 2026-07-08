"""AI-generated image triage — the DIRE gate.

DIRE's real pipeline (the ICCV 2023 paper's actual method) is two GPU/MPI-
bound stages, and its pretrained checkpoint only exists on Baidu/RecDrive —
both often unreachable outside China. If you've gone through that anyway
(via `colab/dire_batch.ipynb`), set DIRE_RESULTS_CSV and results are looked
up by filename.

Otherwise, the default path here is a practical substitute: a general
AI-vs-human image classifier (`Ateeqq/ai-vs-human-image-detector` on
HuggingFace, SigLIP-based, Apache-2.0, runs on CPU, no GPU/MPI/Baidu
needed). It's not the paper's diffusion-reconstruction-error technique —
same honest-substitute pattern as synthid.py's community detector. Weights
download automatically on first use (~400MB, one-time, straight from
HuggingFace over normal HTTPS).

A live-subprocess path (DIRE_SCRIPT/DIRE_MODEL_PATH) is kept for a future
GPU machine running the real DIRE repo, but is unverified — it assumes a
single script that prints JSON, which doesn't match the real
ZhendongWang6/DIRE repo (see README) and would need fixing before relying
on it.
"""
from __future__ import annotations

import csv
import functools
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

METHOD_COLAB_DIRE = "DIRE (official, via colab/dire_batch.ipynb)"
METHOD_LOCAL_CLASSIFIER = "general AI-vs-human image classifier (practical substitute for DIRE)"
METHOD_LIVE_UNVERIFIED = "live DIRE subprocess (unverified path)"
METHOD_UNCONFIGURED = "not configured"


@dataclass
class DIREResult:
    reconstruction_error: float | None
    is_generated: bool | None
    error: str | None = None
    method: str = METHOD_UNCONFIGURED


@functools.lru_cache(maxsize=None)
def _load_results_csv(csv_path: str) -> dict[str, DIREResult]:
    results = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            results[row["filename"]] = DIREResult(
                reconstruction_error=float(row["dire_score"]),
                is_generated=row["is_generated"].strip().lower() == "true",
                method=METHOD_COLAB_DIRE,
            )
    return results


@functools.lru_cache(maxsize=1)
def _load_local_classifier():
    """Lazily load the HuggingFace classifier once per process. Returns
    None if transformers/torch aren't installed, so callers fall through
    to the next path instead of crashing.
    """
    try:
        from transformers import AutoImageProcessor, SiglipForImageClassification
    except ImportError:
        return None
    processor = AutoImageProcessor.from_pretrained("Ateeqq/ai-vs-human-image-detector")
    model = SiglipForImageClassification.from_pretrained("Ateeqq/ai-vs-human-image-detector")
    model.eval()
    return processor, model


def _check_local_classifier(image_path: str | Path) -> DIREResult | None:
    loaded = _load_local_classifier()
    if loaded is None:
        return None
    processor, model = loaded

    import torch
    from PIL import Image

    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as exc:
        return DIREResult(reconstruction_error=None, is_generated=None, error=str(exc), method=METHOD_LOCAL_CLASSIFIER)

    inputs = processor(images=img, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
    label_to_prob = {model.config.id2label[i]: p.item() for i, p in enumerate(probs)}
    ai_prob = label_to_prob.get("ai", 0.0)

    return DIREResult(
        reconstruction_error=round(ai_prob, 4),
        is_generated=ai_prob > 0.5,
        method=METHOD_LOCAL_CLASSIFIER,
    )


def check(
    image_path: str | Path,
    script_path: str | None = None,
    model_path: str | None = None,
    results_csv: str | None = None,
) -> DIREResult:
    """Triage one image as AI-generated or real.

    Priority: DIRE_RESULTS_CSV (real DIRE, if you ran the Colab notebook) ->
    local general classifier (default, no setup needed) -> legacy live
    DIRE_SCRIPT path -> not configured.
    """
    results_csv = results_csv or os.environ.get("DIRE_RESULTS_CSV")
    if results_csv:
        filename = Path(image_path).name
        results = _load_results_csv(results_csv)
        if filename in results:
            return results[filename]
        return DIREResult(
            reconstruction_error=None,
            is_generated=None,
            error=f"{filename} not found in {results_csv} — was it included in the Colab batch?",
            method=METHOD_UNCONFIGURED,
        )

    local_result = _check_local_classifier(image_path)
    if local_result is not None:
        return local_result

    script_path = script_path or os.environ.get("DIRE_SCRIPT")
    model_path = model_path or os.environ.get("DIRE_MODEL_PATH")

    if not script_path or not model_path:
        return DIREResult(
            reconstruction_error=None,
            is_generated=None,
            error="DIRE not configured — install `transformers`/`torch` for the local classifier "
            "(default path), or set DIRE_RESULTS_CSV / DIRE_SCRIPT+DIRE_MODEL_PATH.",
            method=METHOD_UNCONFIGURED,
        )

    proc = subprocess.run(
        # sys.executable, not "python" — bare "python" can resolve to a
        # different interpreter than the one actually running this process
        # (observed on Windows: it silently picked a system install without
        # the venv's packages installed), which fails opaquely downstream.
        [sys.executable, script_path, "--image", str(image_path), "--model", model_path],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return DIREResult(
            reconstruction_error=None, is_generated=None, error=proc.stderr.strip(), method=METHOD_LIVE_UNVERIFIED
        )

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return DIREResult(
            reconstruction_error=None,
            is_generated=None,
            error=f"unparseable output: {exc}",
            method=METHOD_LIVE_UNVERIFIED,
        )

    return DIREResult(
        reconstruction_error=result.get("dire_score"),
        is_generated=result.get("is_generated"),
        method=METHOD_LIVE_UNVERIFIED,
    )
