"""DIRE (DIffusion Reconstruction Error) scoring.

DIRE's real pipeline is two GPU/MPI-bound stages (diffusion reconstruction,
then classification) — impractical on a machine with no GPU. The supported
path here is `colab/dire_batch.ipynb`: run it on Colab's free GPU, download
its `dire_results.csv`, and point DIRE_RESULTS_CSV at it. Results are looked
up by filename.

A live-subprocess path (DIRE_SCRIPT/DIRE_MODEL_PATH) is kept for a future
GPU machine, but is unverified — it assumes a single script that prints
JSON, which doesn't match the real ZhendongWang6/DIRE repo (see README) and
would need fixing before relying on it.
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


@dataclass
class DIREResult:
    reconstruction_error: float | None
    is_generated: bool | None
    error: str | None = None


@functools.lru_cache(maxsize=None)
def _load_results_csv(csv_path: str) -> dict[str, DIREResult]:
    results = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            results[row["filename"]] = DIREResult(
                reconstruction_error=float(row["dire_score"]),
                is_generated=row["is_generated"].strip().lower() == "true",
            )
    return results


def check(
    image_path: str | Path,
    script_path: str | None = None,
    model_path: str | None = None,
    results_csv: str | None = None,
) -> DIREResult:
    """Look up (or, if configured, compute) a DIRE result for one image.

    Checks DIRE_RESULTS_CSV first (see `colab/dire_batch.ipynb`), falling
    back to the live DIRE_SCRIPT/DIRE_MODEL_PATH subprocess path.
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
        )

    script_path = script_path or os.environ.get("DIRE_SCRIPT")
    model_path = model_path or os.environ.get("DIRE_MODEL_PATH")

    if not script_path or not model_path:
        return DIREResult(
            reconstruction_error=None,
            is_generated=None,
            error="DIRE not configured — set DIRE_RESULTS_CSV (see colab/dire_batch.ipynb), "
            "or DIRE_SCRIPT/DIRE_MODEL_PATH for the unverified live path.",
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
        return DIREResult(reconstruction_error=None, is_generated=None, error=proc.stderr.strip())

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return DIREResult(reconstruction_error=None, is_generated=None, error=f"unparseable output: {exc}")

    return DIREResult(
        reconstruction_error=result.get("dire_score"),
        is_generated=result.get("is_generated"),
    )
