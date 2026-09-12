"""
Review workflow endpoints:
  POST  /variants/{variant_id}/approve  -> draft -> approved
  POST  /variants/{variant_id}/reject   -> draft -> rejected (requires a reason)
  PATCH /variants/{variant_id}          -> edit content (draft/rejected only)

All the actual state-machine rules live in app/services/review_workflow.py —
these routes just translate InvalidTransitionError into a clean 409 response
and ContentValidation failures into a 422.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Variant
from app.schemas.variant import VariantResponse, VariantRejectRequest, VariantUpdateRequest
from app.services.constraint_profiles import validate_content
from app.services import review_workflow

router = APIRouter(prefix="/variants", tags=["review"])


def _get_variant_or_404(variant_id: uuid.UUID, db: Session) -> Variant:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Variant {variant_id} not found")
    return variant


@router.post("/{variant_id}/approve", response_model=VariantResponse)
def approve_variant(variant_id: uuid.UUID, db: Session = Depends(get_db)) -> Variant:
    variant = _get_variant_or_404(variant_id, db)
    try:
        review_workflow.approve(variant)
    except review_workflow.InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/{variant_id}/reject", response_model=VariantResponse)
def reject_variant(
    variant_id: uuid.UUID, payload: VariantRejectRequest, db: Session = Depends(get_db)
) -> Variant:
    variant = _get_variant_or_404(variant_id, db)
    try:
        review_workflow.reject(variant, payload.reason)
    except review_workflow.InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.commit()
    db.refresh(variant)
    return variant


@router.patch("/{variant_id}", response_model=VariantResponse)
def edit_variant(
    variant_id: uuid.UUID, payload: VariantUpdateRequest, db: Session = Depends(get_db)
) -> Variant:
    variant = _get_variant_or_404(variant_id, db)

    violations = validate_content(variant.platform, payload.content)
    if violations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Edited content violates constraint profile", "violations": violations},
        )

    try:
        review_workflow.apply_edit(variant, payload.content)
    except review_workflow.InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    db.commit()
    db.refresh(variant)
    return variant