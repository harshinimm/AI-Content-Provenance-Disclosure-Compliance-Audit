"""Legal verdict encoding — translates raw signal survival into the two
statutory tests plus an IP exposure flag. See project guide section 6.

Article 50(2) and SB 942 verdicts are deliberately kept separate: an image
can pass one and fail the other because SB 942 applies a stricter
"extraordinarily difficult to remove" bar rather than Article 50's
"effective, robust, reliable" standard.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalSurvival:
    """Presence of a given signal before/after the transformation battery."""
    pre: bool
    post_all: bool  # survived every transform in the battery, not just one


def article50_verdict(c2pa: SignalSurvival, synthid: SignalSurvival, dire_flags_post: bool | None) -> str:
    marked_pre = c2pa.pre or synthid.pre
    marked_post = c2pa.post_all or synthid.post_all

    if not marked_pre:
        return "Non-Compliant"
    if marked_pre and marked_post:
        base = "Likely Compliant"
    else:
        base = "Marked but not Robust -> Gap"

    if not marked_post and dire_flags_post:
        base += " (nuance: DIRE still detects AI-origin post-strip, but no machine-readable mark survives)"
    return base


def sb942_verdict(c2pa: SignalSurvival, synthid: SignalSurvival) -> str:
    # SB 942 only cares about latent/hidden disclosure and applies a stricter
    # removal-resistance bar than Article 50.
    marked_pre = c2pa.pre or synthid.pre
    marked_post = c2pa.post_all or synthid.post_all

    if not marked_pre:
        return "Non-Compliant"
    if marked_post:
        return "Likely Compliant"
    return "Fails 'extraordinarily difficult to remove' bar -> Non-Compliant"


def ip_flag(has_copyright_claim: bool, c2pa_rights_pre: dict | None, c2pa_rights_post: dict | None) -> str:
    flags = []
    if has_copyright_claim and not c2pa_rights_pre:
        flags.append("Copyrightability Risk")
    if c2pa_rights_pre and not c2pa_rights_post:
        flags.append("Lost Attribution Chain")
    return "; ".join(flags) if flags else "None"
