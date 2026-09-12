"""
Variant status transition rules — the review workflow's state machine.

Centralized here (rather than scattered across route handlers) so the same
rules can be tested independently and reused by both the review API (Day 5)
and the scheduling API (Day 9) — which needs to refuse scheduling anything
that isn't APPROVED. One source of truth for "what's allowed from what state."
"""
from app.db.models.variant import Variant, VariantStatus


class InvalidTransitionError(Exception):
    """Raised when a status transition isn't allowed from the variant's current state."""


def approve(variant: Variant) -> None:
    if variant.status != VariantStatus.DRAFT:
        raise InvalidTransitionError(
            f"Cannot approve a variant with status '{variant.status.value}'; "
            f"only draft variants can be approved."
        )
    variant.status = VariantStatus.APPROVED
    variant.rejection_reason = None


def reject(variant: Variant, reason: str) -> None:
    if variant.status != VariantStatus.DRAFT:
        raise InvalidTransitionError(
            f"Cannot reject a variant with status '{variant.status.value}'; "
            f"only draft variants can be rejected."
        )
    variant.status = VariantStatus.REJECTED
    variant.rejection_reason = reason


def apply_edit(variant: Variant, new_content: str) -> None:
    """
    Editing is allowed from DRAFT (stays DRAFT) or REJECTED (moves back to
    DRAFT, clearing the old rejection reason — a natural "fix it and
    resubmit" flow). Approved/published variants can't be edited in place;
    that would silently change content that was already signed off on.
    """
    if variant.status not in (VariantStatus.DRAFT, VariantStatus.REJECTED):
        raise InvalidTransitionError(
            f"Cannot edit a variant with status '{variant.status.value}'; "
            f"only draft or rejected variants can be edited."
        )
    variant.content = new_content
    if variant.status == VariantStatus.REJECTED:
        variant.status = VariantStatus.DRAFT
        variant.rejection_reason = None


def ensure_schedulable(variant: Variant) -> None:
    """
    Used by the Day 9 scheduling endpoint. Refuses anything that isn't
    APPROVED — this is the actual enforcement of "an unapproved variant
    can never be scheduled" from the brief.
    """
    if variant.status != VariantStatus.APPROVED:
        raise InvalidTransitionError(
            f"Cannot schedule a variant with status '{variant.status.value}'; "
            f"only approved variants can be scheduled."
        )