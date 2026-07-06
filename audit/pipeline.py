"""Per-image pipeline: DIRE triage gate -> baseline checks -> transformation
battery -> re-check -> verdicts. Implements Steps 1-4 from the project guide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import c2pa, dire, synthid, transforms
from .synthid import METHOD_UNOFFICIAL
from .verdict import SignalSurvival, article50_verdict, ip_flag, sb942_verdict


@dataclass
class ImageAuditRow:
    source: str
    tool: str
    c2pa_pre: bool
    c2pa_post: bool
    synthid_pre: bool | None
    synthid_post: bool | None
    synthid_pre_method: str
    synthid_post_method: str
    synthid_pre_score: float | None
    synthid_post_score: float | None
    dire_pre: float | None
    dire_post: float | None
    article50_verdict: str
    sb942_verdict: str
    ip_flag: str
    notes: list[str] = field(default_factory=list)


NOT_FLAGGED_VERDICT = "Not Applicable — DIRE did not flag as AI-generated"
NOT_RUN_METHOD = "not run (DIRE triaged out)"


def run_image(
    image_path: str | Path,
    tool: str,
    synthid_pre_manual: bool | None = None,
    synthid_post_manual: bool | None = None,
    has_copyright_claim: bool = True,
) -> ImageAuditRow:
    src = Path(image_path)
    notes: list[str] = []

    # Step 1 — DIRE triage gate. Only images DIRE actually flags as
    # generated (or that DIRE can't classify at all, e.g. not configured)
    # proceed to the expensive C2PA/SynthID/transform checks below — this
    # is what lets --url scale to hundreds of scraped images instead of
    # running the full pipeline on everything. `is_generated is False` is
    # an explicit real-photo classification; None means DIRE errored or
    # isn't set up, which fails open (still runs full checks) rather than
    # silently skipping everything.
    dire_pre_result = dire.check(src)
    if dire_pre_result.error:
        notes.append(f"DIRE pre-check: {dire_pre_result.error}")

    if dire_pre_result.is_generated is False:
        notes.append(
            f"Skipped C2PA/SynthID/transform checks — DIRE classified as real "
            f"(reconstruction_error={dire_pre_result.reconstruction_error})"
        )
        return ImageAuditRow(
            source=str(src),
            tool=tool,
            c2pa_pre=False,
            c2pa_post=False,
            synthid_pre=None,
            synthid_post=None,
            synthid_pre_method=NOT_RUN_METHOD,
            synthid_post_method=NOT_RUN_METHOD,
            synthid_pre_score=None,
            synthid_post_score=None,
            dire_pre=dire_pre_result.reconstruction_error,
            dire_post=None,
            article50_verdict=NOT_FLAGGED_VERDICT,
            sb942_verdict=NOT_FLAGGED_VERDICT,
            ip_flag="None",
            notes=notes,
        )

    # Step 2 — baseline checks (pre-transformation), DIRE-flagged subset only
    c2pa_pre_result = c2pa.check(src)
    synthid_pre_result = synthid.check(str(src), manual_override=synthid_pre_manual)

    if c2pa_pre_result.error:
        notes.append(f"C2PA pre-check: {c2pa_pre_result.error}")
    if synthid_pre_result.notes:
        notes.append(f"SynthID pre-check: {synthid_pre_result.notes}")
    if synthid_pre_result.method == METHOD_UNOFFICIAL:
        notes.append(
            "SynthID pre-check used an unofficial community-detector estimate "
            "(trained on GPT-Image-2 only) — not Google's own verification"
        )

    # Step 3 — transformation battery
    variants = transforms.apply_battery(src)

    # Step 4 — re-run checks on every variant; "post" signal only counts as
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

    synthid_post_result = synthid.check(
        str(next(iter(variants.values()))), manual_override=synthid_post_manual
    )
    if synthid_post_result.notes:
        notes.append(f"SynthID post-check: {synthid_post_result.notes}")
    if synthid_post_result.method == METHOD_UNOFFICIAL:
        notes.append(
            "SynthID post-check used an unofficial community-detector estimate "
            "(trained on GPT-Image-2 only) — not Google's own verification"
        )

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
        synthid_pre_method=synthid_pre_result.method,
        synthid_post_method=synthid_post_result.method,
        synthid_pre_score=synthid_pre_result.score,
        synthid_post_score=synthid_post_result.score,
        dire_pre=dire_pre_result.reconstruction_error,
        dire_post=sum(dire_post_scores) / len(dire_post_scores) if dire_post_scores else None,
        article50_verdict=a50,
        sb942_verdict=sb942,
        ip_flag=ip,
        notes=notes,
    )
