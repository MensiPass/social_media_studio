"""
Seed script: populates the database with a small demo dataset so anyone
(including an evaluator) can see the system in a working, non-empty state
immediately after setup, without manually walking through every step.

Creates one post, generates variants for all 4 platforms, and approves
the X variant as a demonstration of the review workflow.

Run with:
    python scripts/seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.db.models import Post, Variant
from app.db.models.variant import Platform, VariantStatus
from app.services.variant_generator import generate_variant_text
from app.services.constraint_profiles import validate_content


def main() -> None:
    db = SessionLocal()
    try:
        post = Post(
            source_type="markdown",
            source_content=(
                "# The Secret Life of Red Foxes\n\n"
                "Red foxes are remarkably adaptable animals found across the entire "
                "Northern Hemisphere, thriving in forests, grasslands, mountains, "
                "and even cities. They are known for their cunning hunting "
                "strategies and striking reddish coats."
            ),
            title="The Secret Life of Red Foxes",
        )
        db.add(post)
        db.commit()
        print(f" Created seed post: {post.id}")

        created = []
        for platform in Platform:
            text = generate_variant_text(post, platform)
            violations = validate_content(platform, text)
            if violations:
                print(f"     Skipped {platform.value}: {violations}")
                continue
            variant = Variant(post_id=post.id, platform=platform, content=text)
            db.add(variant)
            created.append(variant)
        db.commit()
        print(f" Created {len(created)} draft variants (one per platform)")

        x_variant = next((v for v in created if v.platform == Platform.X), None)
        if x_variant:
            x_variant.status = VariantStatus.APPROVED
            db.commit()
            print(f" Approved the X variant ({x_variant.id}) as a review-workflow demo")

        print("\nSeed complete. Try, for example:")
        print(f"  GET  /posts/{post.id}")
        print(f"  GET  /posts/{post.id}/variants")
        if x_variant:
            print(f"  POST /variants/{x_variant.id}/schedule")

    finally:
        db.close()


if __name__ == "__main__":
    main()