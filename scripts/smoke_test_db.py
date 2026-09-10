"""
Smoke test: verifies the SQLAlchemy models actually work against your REAL
Postgres database (not SQLite) — before we hand schema control over to Alembic.

Why this matters: SQLite is forgiving about things Postgres is strict about
(e.g. native UUID columns, native ENUM types). This catches those problems
now, while the fix is a one-line model change — not after `alembic upgrade
head` has already written a migration file around a mistake.

What it does, in order:
  1. Connects to Postgres using the same settings.database_url as the app.
  2. Creates all 4 tables directly (bypassing Alembic).
  3. Inserts a test Post + Variant, reads them back, checks the relationship.
  4. Cleans up: drops all 4 tables again, so Postgres is empty afterward —
     leaving it in the correct state for Alembic's autogenerate step next.

Run with:
    python scripts/smoke_test_db.py
"""
import sys
from pathlib import Path

# Make sure "app" is importable regardless of where this script is run from
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.models import Post, Variant, Platform, VariantStatus


def main() -> None:
    print(f"Connecting to: {settings.database_url}")

    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print("\n❌ Could not connect to Postgres.")
        print(f"   Error: {exc}")
        print("\n   Checklist:")
        print("   - Did you run `docker compose up -d`?")
        print("   - Does `docker compose ps` show postgres as 'healthy'?")
        print("   - Does DATABASE_URL in your .env match docker-compose.yml?")
        sys.exit(1)

    print("✅ Connected to Postgres.\n")

    print("Creating tables directly from models (bypassing Alembic)...")
    Base.metadata.create_all(engine)
    created_tables = sorted(Base.metadata.tables.keys())
    print(f"✅ Tables created: {created_tables}\n")

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("Inserting a test Post + Variant...")
        post = Post(
            source_type="markdown",
            source_content="# Red foxes are clever",
            title="Red Foxes (smoke test)",
        )
        variant = Variant(
            post=post,
            platform=Platform.LINKEDIN,
            content="Did you know foxes are clever? #wildlife",
        )
        db.add(post)
        db.commit()

        fetched = db.query(Post).filter_by(title="Red Foxes (smoke test)").first()
        assert fetched is not None, "Post was not saved"
        assert len(fetched.variants) == 1, "Variant relationship did not save correctly"
        assert fetched.variants[0].platform == Platform.LINKEDIN
        assert fetched.variants[0].status == VariantStatus.DRAFT

        print("✅ Post saved and read back correctly.")
        print(f"✅ Variant relationship works — platform={fetched.variants[0].platform.value}, "
              f"status={fetched.variants[0].status.value} (default applied correctly)\n")

    finally:
        print("Cleaning up: deleting test row and dropping all tables...")
        db.rollback()
        db.close()
        # Drop everything so Postgres is empty again — Alembic's autogenerate
        # step needs a clean slate to correctly detect "create everything".
        Base.metadata.drop_all(engine)
        print("✅ Cleanup complete. Postgres is empty and ready for Alembic.\n")

    print("SMOKE TEST PASSED — models are confirmed working against real Postgres.")


if __name__ == "__main__":
    main()