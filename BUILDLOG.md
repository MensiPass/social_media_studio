# Build Log — AI Usage

Honest log of where AI (Claude) helped, where it was wrong, and what was changed.
Updated daily.

---

## Day 1 — Environment & skeleton

**Where AI helped:**
- Scaffolded the repo folder structure and `docker-compose.yml`.
- Generated `app/core/config.py` (typed settings loader pattern using pydantic-settings).
- Diagnosed and fixed a real dependency compatibility issue: the originally
  pinned `pydantic`/`pydantic-core` version had no prebuilt wheel for Python 3.14,
  which would have failed on install. Verified a working version set
  (`pydantic==2.13.5`, resolving `pydantic-core==2.46.5`) before handing it over.

**What I understand and can explain:**
- Why `.env` is git-ignored but `.env.example` is committed.
- Why settings are loaded once into a typed object instead of reading `os.environ`
  scattered across files — fails fast on a missing/misspelled variable.
- Why Postgres/Redis run in Docker but the FastAPI app runs directly on the host
  for now (faster dev loop; no rebuild needed on every code change).
- Why the exact pinned versions in requirements.txt matter — compiled Python
  packages (like pydantic-core, psycopg) ship prebuilt binaries per Python version,
  and a version with no matching binary for your Python version will fail to install.

**What I changed / would change:**
- (fill in as you make your own edits)

## Day 3 — Post ingestion

**Where AI helped:**
- Designed the Pydantic schema split (PostCreate vs PostResponse) and the
  content_fetcher service for URL text extraction.
- Wrote scripts/smoke_test_api.py using FastAPI's dependency override system
  to test route logic without needing a live Postgres connection.

**What I understand and can explain:**
- Why source_type determines whether we fetch-and-extract or store raw text.
- Why a failed URL fetch returns 422, not 500 — it's bad client input, not a
  server failure.
- Why the smoke test needed `poolclass=StaticPool` for SQLite specifically —
  a SQLite-in-memory quirk where each new connection gets a separate empty
  database unless forced to reuse one connection.

**What I changed / would change:**
- Fixed a real-world issue: Wikipedia (and similar sites) reject requests
  with non-browser User-Agent headers, returning 403. Our error handling
  worked correctly (clean 4xx, not a crash) — the fix was using a realistic
  browser User-Agent string so legitimate fetches succeed.