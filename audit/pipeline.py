"""Per-image pipeline: baseline checks -> transformation battery -> re-check
-> verdicts. Implements steps A-C from the project guide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import c2pa, dire, synthid, transforms
from .verdict import SignalSurvival, article50_verdict, ip_flag, sb942_verdict


@dataclass
class ImageAuditRow:
    source: str
    tool: str
    c2pa_pre: bool
    c2pa_post: bool
    synthid_pre: bool | None
    synthid_post: bool | None
    dire_pre: float | None
    dire_post: float | None
    article50_verdict: str
    sb942_verdict: str
    ip_flag: str
    notes: list[str] = field(default_factory=list)


def run_image(
    image_path: str | Path,
    tool: str,
    synthid_pre_manual: bool | None = None,
    synthid_post_manual: bool | None = None,
    has_copyright_claim: bool = True,
) -> ImageAuditRow:
    src = Path(image_path)
    notes: list[str] = []

    # Step A — baseline (pre-transformation)
    c2pa_pre_result = c2pa.check(src)
    synthid_pre_result = synthid.check(str(src), manual_result=synthid_pre_manual)
    dire_pre_result = dire.check(src)

    for result, label in ((c2pa_pre_result, "C2PA"), (dire_pre_result, "DIRE")):
        if result.error:
            notes.append(f"{label} pre-check: {result.error}")
    if synthid_pre_result.detected is None:
        notes.append("SynthID pre-check pending manual verification")

    # Step B — transformation battery
    variants = transforms.apply_battery(src)

    # Step C — re-run checks on every variant; "post" signal only counts as
    # surviving if it survives ALL transforms, per the guide's robustness bar
    c2pa_post_all = True
    dire_post_scores: list[float] = []
    dire_post_any_generated = False
    for name, variant_path in variants.items():
        c2pa_variant = c2pa.check(variant_path)
        c2pa_post_all = c2pa_post_all and c2pa_variant.present

        dire_variant = dire.check(variant_path)
        if dire_variant.reconstruction_error is not None:
            dire_post_scores.append(dire_variant.reconstruction_error)
        if dire_variant.is_generated:
            dire_post_any_generated = True

    synthid_post_result = synthid.check(str(next(iter(variants.values()))), manual_result=synthid_post_manual)
    if synthid_post_result.detected is None:
        notes.append("SynthID post-check pending manual verification")

    c2pa_survival = SignalSurvival(pre=c2pa_pre_result.present, post_all=c2pa_post_all)
    synthid_survival = SignalSurvival(
        pre=bool(synthid_pre_result.detected),
        post_all=bool(synthid_post_result.detected),
    )

    a50 = article50_verdict(c2pa_survival, synthid_survival, dire_flags_post=dire_post_any_generated)
    sb942 = sb942_verdict(c2pa_survival, synthid_survival)
    ip = ip_flag(
        has_copyright_claim=has_copyright_claim,
        c2pa_rights_pre=c2pa_pre_result.rights_fields,
        c2pa_rights_post=c2pa_pre_result.rights_fields if c2pa_post_all else None,
    )

    return ImageAuditRow(
        source=str(src),
        tool=tool,
        c2pa_pre=c2pa_pre_result.present,
        c2pa_post=c2pa_post_all,
        synthid_pre=synthid_pre_result.detected,
        synthid_post=synthid_post_result.detected,
        dire_pre=dire_pre_result.reconstruction_error,
        dire_post=sum(dire_post_scores) / len(dire_post_scores) if dire_post_scores else None,
        article50_verdict=a50,
        sb942_verdict=sb942,
        ip_flag=ip,
        notes=notes,
    )
