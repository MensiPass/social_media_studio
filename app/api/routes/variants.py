"""
Variant endpoints:
  POST /posts/{post_id}/variants/generate  -> auto-generate one variant per platform
  POST /posts/{post_id}/variants           -> manually create one variant
  GET  /posts/{post_id}/variants           -> list variants for a post
  GET  /variants/{variant_id}              -> fetch a single variant

Every path into variant creation — generated or manual — runs through the
SAME constraint validation (validate_content). A rule-breaking variant is
never stored; it's reported back with the specific reason(s) it failed,
before it ever reaches the review workflow (Day 5).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Post, Variant
from app.db.models.variant import Platform
from app.schemas.variant import (
    VariantCreate,
    VariantResponse,
    GenerateVariantsResponse,
    BlockedVariant,
)
from app.services.constraint_profiles import validate_content
from app.services.variant_generator import generate_variant_text

router = APIRouter(tags=["variants"])


def _get_post_or_404(post_id: uuid.UUID, db: Session) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Post {post_id} not found")
    return post


@router.post(
    "/posts/{post_id}/variants/generate",
    response_model=GenerateVariantsResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_variants(post_id: uuid.UUID, db: Session = Depends(get_db)) -> GenerateVariantsResponse:
    post = _get_post_or_404(post_id, db)

    created: list[Variant] = []
    blocked: list[BlockedVariant] = []

    for platform in Platform:
        draft_text = generate_variant_text(post, platform)
        violations = validate_content(platform, draft_text)

        if violations:
            blocked.append(BlockedVariant(platform=platform, reasons=violations))
            continue

        variant = Variant(post_id=post.id, platform=platform, content=draft_text)
        db.add(variant)
        created.append(variant)

    db.commit()
    for v in created:
        db.refresh(v)

    return GenerateVariantsResponse(created=created, blocked=blocked)


@router.post(
    "/posts/{post_id}/variants",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_variant_manually(
    post_id: uuid.UUID, payload: VariantCreate, db: Session = Depends(get_db)
) -> Variant:
    post = _get_post_or_404(post_id, db)

    violations = validate_content(payload.platform, payload.content)
    if violations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Variant violates constraint profile",
                "violations": violations,
            },
        )

    variant = Variant(post_id=post.id, platform=payload.platform, content=payload.content)
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.get("/posts/{post_id}/variants", response_model=list[VariantResponse])
def list_variants_for_post(post_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Variant]:
    _get_post_or_404(post_id, db)
    return (
        db.query(Variant)
        .filter(Variant.post_id == post_id)
        .order_by(Variant.created_at)
        .all()
    )


@router.get("/variants/{variant_id}", response_model=VariantResponse)
def get_variant(variant_id: uuid.UUID, db: Session = Depends(get_db)) -> Variant:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Variant {variant_id} not found")
    return variant