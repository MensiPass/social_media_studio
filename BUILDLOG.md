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


  ## Day 8 — LinkedIn adapter (real, OAuth)

**Where AI helped:**
- Researched LinkedIn's CURRENT API (it deprecated the old UGC Posts
  endpoint in favor of /rest/posts, and requires a monthly-versioned
  LinkedIn-Version header) before writing any code, to avoid building
  against stale documentation.
- Made LINKEDIN_API_VERSION a .env value rather than hardcoded, since
  LinkedIn ships a new version every month — this avoids the adapter
  silently breaking a few weeks after being written.
- Built the OAuth 2.0 Authorization Code flow (login -> LinkedIn consent ->
  callback -> token exchange -> fetch member URN) as two simple endpoints,
  deliberately without automatic token refresh — tokens last ~60 days, and
  re-running the flow by hand when needed is simpler and more honest than
  building refresh-token infrastructure this capstone doesn't need yet.

**What I understand and can explain:**
- Why the person URN (not just the access token) is needed to post — it's
  the "author" field LinkedIn's Posts API requires, obtained once via
  /v2/userinfo using the OpenID Connect scope.
- Why the OAuth callback checks the returned `state` against a set of
  values we generated — this is CSRF protection, preventing a forged
  callback from being accepted.
- Why LinkedIn returns the new post's ID in a response HEADER
  (x-restli-id) rather than the body — a Rest.li API convention, different
  from Telegram's JSON-body response.

**What I changed / would change:**
- Hit the same stale-server-on-port-8000 issue as Day 5 when checking
  registered routes — same root cause (leftover process from an earlier
  session), resolved the same way (netstat + taskkill).


  ## Day 9 — Celery + Redis background scheduling

**Where AI helped:**
- Designed the two-task split (check_due_slots + publish_slot) with an
  explicit "claim before dispatch" step — PENDING -> PUBLISHING happens
  and commits BEFORE any task is enqueued, so a slot is never left claimed
  without work actually dispatched for it.
- Used module-qualified session access (`db_session.SessionLocal()`
  instead of `from app.db.session import SessionLocal`) specifically so
  tests could monkeypatch the session and exercise the real task functions
  against SQLite without needing live Postgres/Redis.
- Wrote scripts/smoke_test_scheduling.py using Celery's task_always_eager
  mode to test the full claim-dispatch-publish cycle synchronously,
  including confirming a completed slot is never reclaimed and a future
  slot is correctly left alone.

**What I understand and can explain:**
- Why Beat re-reads the database every tick instead of keeping its own
  schedule in memory — this is what makes the scheduler itself restartable
  without losing track of anything.
- Why claiming happens in its own transaction, committed before any task
  is enqueued — the ordering matters: claim-then-enqueue means the worst
  case on a crash is a stuck PUBLISHING slot (fixable), never a duplicate
  publish from double-dispatch.

**What I changed / would change — two real infrastructure issues hit and fixed:**

1. **Windows + Celery's default `prefork` pool is broken.** The worker
   crashed immediately with `PermissionError: [WinError 5] Access is
   denied` from `billiard` (Celery's multiprocessing library) — a known
   Windows incompatibility with the default worker pool. Fixed by running
   with `--pool=solo` instead, which uses a single process instead of a
   multiprocessing pool. Fine for this project's scale.

2. **Local time vs. UTC confusion during manual testing.** Celery's log
   timestamps print in local system time, not UTC. I initially asked for a
   test time based on matching the log's displayed clock to a "1 minute
   from now" guess, without accounting for the ~2 hour UTC offset — the
   slot was correctly NOT claimed for over 10 minutes because, in real
   UTC terms, it genuinely wasn't due yet. The actual scheduling logic was
   correct the entire time. Fixed by computing the scheduled_at value with
   `datetime.now(timezone.utc)` in Python directly, rather than eyeballing
   a time from local log output — removes the human timezone-math step
   entirely.


   ## Day 10 — Idempotency + crash recovery

**Where AI helped:**
- Designed two separate idempotency guards in publish_slot rather than
  one: guard #1 (status==COMPLETED) handles the common retry case cheaply;
  guard #2 (existing successful PublishAttempt) handles the narrower case
  where a crash happened between recording success and updating status.
- Designed recover_stuck_slots as a fully separate periodic task rather
  than folding recovery logic into check_due_slots — keeps "find new work"
  and "recover abandoned work" as clearly separate concerns.
- Documented an honest, known limitation in the code and here: a crash in
  the exact window between the external platform accepting a post and our
  DB recording that success is not fully solvable without the external
  platform itself supporting idempotency keys (which Telegram/LinkedIn
  don't for posts). This is an industry-standard hard limit, not a gap in
  our design — what we guarantee is no duplicate from retries or from
  recovering genuinely-abandoned work.

**What I understand and can explain:**
- Why recover_stuck_slots is safe to call as often as we like, even
  redundantly — it's the idempotency guards in publish_slot that make
  re-dispatching harmless, not any special logic in recovery itself.
- Why updated_at (not created_at) is what crash recovery checks — it needs
  to know when the slot was last CLAIMED, not when it was originally
  scheduled.

**What I changed / would change — two real issues hit and fixed during live testing:**

1. **Postgres enum labels are the Python enum's NAME, not its `.value`.**
   A manual SQL UPDATE using lowercase 'publishing' (matching the JSON API's
   serialized form) failed with "invalid input value for enum
   slot_status_enum". SQLAlchemy's Enum type stores each member's `.name`
   (uppercase, e.g. PUBLISHING) as the actual database label by default —
   the lowercase value seen in API responses is a separate, cosmetic
   Pydantic serialization layer. Only affects raw SQL written by hand; the
   application code itself never hits this since SQLAlchemy translates
   transparently. Fixed by using the uppercase label in the manual query.

2. **Bash variable scope across terminal sessions.** An earlier attempt at
   the crash-recovery test failed because $SLOT_ID was set in one command
   block but referenced in a separate terminal invocation where it didn't
   exist — not a code bug, a shell-session mistake. Fixed by keeping all
   dependent commands in one continuous terminal session.


   ## Day 11 — Publish history + hardening

**Where AI helped:**
- Built /history and /schedule/{id}/attempts as a join across
  PublishAttempt -> ScheduleSlot -> Variant, so each entry is
  self-contained (platform, scheduled time, actual attempt time) without
  requiring the caller to stitch together separate lookups.
- Converted the ad-hoc smoke_test_*.py scripts into a real, discoverable
  pytest suite (tests/conftest.py fixtures + tests/test_review_workflow.py
  + tests/test_adapters.py) — capstone.yaml has always declared `test:
  pytest`, but until today that command found zero tests. Deliberately
  kept the Telegram/LinkedIn LIVE scripts out of the pytest suite so
  running `pytest` never sends a real message or post.
- Reused an existing tests/conftest.py found already in place (fixtures
  `client` and `db`) rather than duplicating a slightly different version —
  one source of truth for test fixtures.

**What I understand and can explain:**
- Why the idempotency/crash-recovery tests need their OWN fixture
  (task_db) rather than the shared client/db fixtures — they need to patch
  app.db.session.SessionLocal AND enable Celery's eager mode, which is
  more setup than a plain API test needs.
- Why Telegram/LinkedIn's real network tests are scripts, not pytest
  tests — a test suite that might text a real Telegram chat or post to a
  real LinkedIn profile every time someone runs `pytest` would be
  actively harmful, not just slow.

**What I changed / would change:**
- (none needed — clean run, matched sandbox verification exactly)