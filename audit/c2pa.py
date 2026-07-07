"""Wrapper around c2patool for reading/verifying C2PA manifests.

The standalone contentauth/c2patool repo is archived; get it from the
cli/ crate of contentauth/c2pa-rs (see README). Set C2PATOOL_PATH to the
binary if it isn't on PATH.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class C2PAResult:
    present: bool
    manifest: dict[str, Any] | None
    rights_fields: dict[str, Any] | None
    error: str | None = None


def _extract_rights_fields(manifest: dict[str, Any]) -> dict[str, Any]:
    """Pull authorship/rights/licensing assertions out of a manifest, if present.

    c2patool's JSON shape varies by manifest producer, so this walks the
    known assertion label patterns rather than assuming a fixed schema.
    """
    rights: dict[str, Any] = {}
    manifests = manifest.get("manifests", {})
    active_label = manifest.get("active_manifest")
    active = manifests.get(active_label, {}) if active_label else next(iter(manifests.values()), {})

    for assertion in active.get("assertions", []):
        label = assertion.get("label", "")
        if "creativeWork" in label or "author" in label.lower():
            rights[label] = assertion.get("data")
        if label.startswith("c2pa.actions"):
            rights.setdefault("actions", assertion.get("data"))

    claim_generator = active.get("claim_generator")
    if claim_generator:
        rights["claim_generator"] = claim_generator

    return rights


def check(image_path: str | Path) -> C2PAResult:
    """Run c2patool against a single image and parse the manifest, if any."""
    binary = os.environ.get("C2PATOOL_PATH") or shutil.which("c2patool")
    if binary is None:
        return C2PAResult(
            present=False,
            manifest=None,
            rights_fields=None,
            error="c2patool not found — set C2PATOOL_PATH or put it on PATH "
            "(see README for install instructions)",
        )

    proc = subprocess.run(
        [binary, str(image_path)],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0 or not proc.stdout.strip():
        # No manifest is a valid (and expected) outcome, not necessarily a tool error.
        return C2PAResult(present=False, manifest=None, rights_fields=None, error=proc.stderr.strip() or None)

    try:
        manifest = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return C2PAResult(present=False, manifest=None, rights_fields=None, error=f"unparseable output: {exc}")

    return C2PAResult(
        present=True,
        manifest=manifest,
        rights_fields=_extract_rights_fields(manifest),
    )
