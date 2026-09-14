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

  ## Day 4 — Variant generation + constraint profiles

**Where AI helped:**
- Designed the constraint profile data structure (per-platform max_length,
  max_hashtags) using real platform limits (X 280 chars, LinkedIn 3000,
  Instagram 2200 chars/30 hashtags, Telegram 4096 chars).
- Wrote the template-based generator (deterministic, no AI/API key needed —
  chose this over a real AI model for simplicity and zero external dependencies).
- Wrote scripts/smoke_test_variants.py covering both the happy path (4/4
  platforms generate successfully) and the required "bad variant blocked"
  evidence (length violation and hashtag violation, each with 422 + reason).

**What I understand and can explain:**
- Why generation and validation are separate functions — the generator
  tries to produce good content, but validation is the sole authority on
  whether it gets stored. A manually-submitted variant and a generated one
  go through the exact same validation path.
- Why the /generate endpoint reports "blocked" platforms in its response
  instead of failing the whole request — some platforms can succeed while
  others are blocked, and the caller needs visibility into both outcomes.

**What I changed / would change:**
- Caught my own mistake in an example curl command — the first attempt to
  demonstrate a blocked variant used text that was actually under X's 280
  character limit (116 chars), so it was correctly accepted. Not a bug —
  just a bad test input. Fixed by using genuinely oversized text (336 chars)
  and confirmed the 422 + exact violation message.


  ## Day 5 — Review workflow

**Where AI helped:**
- Designed the state machine as a standalone module (review_workflow.py)
  rather than inline route logic — so the same approve/reject/edit rules,
  and specifically the "must be approved to schedule" guard, can be reused
  unchanged by Day 9's scheduler.
- Wrote both a pure state-machine unit test and a full API-level smoke test.

**What I understand and can explain:**
- Why editing a REJECTED variant resets it to DRAFT and clears the rejection
  reason — a "fix it and resubmit" flow, not a silent edit.
- Why approved/published variants can't be edited in place — that would
  silently change content someone already signed off on.
- Why content validation runs before the state-transition check in the edit
  endpoint — a clearer error for the caller either way, but content rules
  are checked first since that's usually the more actionable fix.

**What I changed / would change:**
- Diagnosed a false alarm: an early server route check showed missing
  endpoints, which looked like a wiring bug. Root cause was two stale
  uvicorn processes still bound to port 8000 from earlier days, one of
  which answered the check with an outdated app version. Killed both
  and confirmed the real server has all 9 expected endpoints registered.

  ## Day 6 — Adapter interface + mock adapters

**Where AI helped:**
- Designed the SocialPublisher ABC and PublishResult dataclass — chose to
  make PublishResult's fields (success, external_post_id, detail) line up
  exactly with the publish_attempts table columns from Day 2, so Day 9's
  worker can convert one directly into the other with no translation logic.
- Designed the registry as a single dict mapping Platform -> publisher
  instance, with real adapters (Telegram/LinkedIn) intentionally left
  unregistered until Days 7-8, raising a clear NotImplementedError instead
  of failing silently.

**What I understand and can explain:**
- Why SocialPublisher is an ABC (abstract base class) instead of a plain
  class with a method that does nothing — Python refuses to instantiate it
  directly, catching a forgotten implementation at object-creation time
  instead of at first use.
- Why publish() is documented to return a failure result rather than raise
  an exception for expected failures — this keeps Day 9's worker loop
  simple: it always gets a PublishResult back, never has to guess whether
  a try/except is needed for "the platform was just down."
- Why the registry holds shared instances rather than creating a new
  publisher per call — mirrors how a real adapter (e.g. Telegram) would
  want to reuse one HTTP client instead of creating a new one per post.

**What I changed / would change:**
- (none needed — first clean run)

## Day 7 — Telegram adapter (real)

**Where AI helped:**
- Wrote the real TelegramPublisher against Telegram's Bot API (sendMessage
  endpoint), following the same PublishResult contract as the mock adapters
  — no special-casing needed anywhere else in the codebase for "this one's
  real."
- Split testing into two layers: a mocked unit test (error-handling logic,
  runs anywhere, no credentials) and a separate live test (real send, only
  runs with real .env credentials) — so the general test suite never spams
  a real Telegram chat on every run.

**What I understand and can explain:**
- Why publish() catches httpx.RequestError and non-"ok" API responses and
  converts both into a PublishResult(success=False, ...) instead of letting
  exceptions propagate — matches the interface contract from Day 6 exactly.
- Why the bot needs a message sent TO it first before getUpdates returns
  anything — Telegram only shows updates the bot has actually received,
  it can't discover a chat_id it's never seen traffic from.
- The difference between a bot's numeric chat_id (from getUpdates, used
  for DMs) versus a channel's @username (usable directly as chat_id for
  public channels) — used the DM approach here for simplicity.

**What I changed / would change:**
- First getUpdates attempt returned {"ok":false,"error_code":404}. Root
  cause: the literal placeholder text wasn't replaced with the real token
  in the URL. Fixed by confirming the exact token substitution — no code
  change needed, just a URL construction mistake on my part while testing.