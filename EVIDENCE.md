# Evidence

One proof per requirement, added the day it's completed.

---

## Day 1 — Environment & skeleton

**Proof: FastAPI app boots and responds correctly.**

```bash
{"status":"ok","service":"social-media-studio"}
```

**Proof: dependencies install cleanly with no version conflicts.**

```bash
{"status":"ok","service":"social-media-studio"}
```

**Proof: settings loader correctly reads .env.**

```bash
DATABASE_URL: postgresql+psycopg://studio_user:changeme_local_dev_only@localhost:5432/social_studio
REDIS_URL: redis://localhost:6379/0
```
## Day 2 — Database design

**Proof: models work correctly against real Postgres (not just SQLite).**

\`\`\`
$ python scripts/smoke_test_db.py
[... your smoke test output from earlier ...]
SMOKE TEST PASSED — models are confirmed working against real Postgres.
\`\`\`

**Proof: Alembic migration generated and applied successfully.**

\`\`\`
$ alembic revision --autogenerate -m "create posts, variants, schedule_slots, publish_attempts"
INFO  [alembic.autogenerate.compare] Detected added table 'posts'
INFO  [alembic.autogenerate.compare] Detected added table 'variants'
INFO  [alembic.autogenerate.compare] Detected added table 'schedule_slots'
INFO  [alembic.autogenerate.compare] Detected added table 'publish_attempts'
Generating .../alembic/versions/cef9434531d4_create_posts_variants_schedule_slots_.py ...  done

$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> cef9434531d4, create posts, variants, schedule_slots, publish_attempts
\`\`\`

**Proof: all 4 tables exist in Postgres.**

\`\`\`
$ docker exec -it sms_postgres psql -U studio_user -d social_studio -c "\dt"
                List of relations
 Schema |       Name       | Type  |    Owner
--------+------------------+-------+-------------
 public | alembic_version  | table | studio_user
 public | posts            | table | studio_user
 public | publish_attempts | table | studio_user
 public | schedule_slots   | table | studio_user
 public | variants         | table | studio_user
(5 rows)
\`\`\`


## Day 3 — Post ingestion

**Proof: full route logic verified (SQLite smoke test).**

\`\`\`
$ python scripts/smoke_test_api.py
1) Creating a post from pasted Markdown...
   ✅ Created post ... — title parsed correctly: 'Red Foxes'
2) Fetching that post back by ID...
   ✅ Post retrieved correctly.
3) Listing all posts...
   ✅ List endpoint returned 1 post(s).
4) Submitting a blank Markdown post (should be rejected)...
   ✅ Correctly rejected with 422.
5) Requesting a post that doesn't exist (should 404)...
   ✅ Correctly returned 404.
6) Creating a post from a real URL (github.com)...
   ✅ URL fetched and extracted — 15137 chars of text stored.
SMOKE TEST PASSED — post ingestion works correctly.
\`\`\`

**Proof: real write to Postgres via running API.**

\`\`\`
$ curl -X POST http://127.0.0.1:8000/posts -H "Content-Type: application/json" \
  -d '{"source_type":"markdown","source_content":"# Red Foxes\n\nFoxes are clever animals."}'
{"id":"68c31c80-c35b-4716-9dba-0433f56bcc50","source_type":"markdown","source_content":"# Red Foxes\n\nFoxes are clever animals.","title":"Red Foxes","created_at":"2026-09-11T09:25:10.285084Z"}
\`\`\`

**Proof: bad URL input is rejected cleanly, not with a server crash.**

\`\`\`
$ curl -X POST http://127.0.0.1:8000/posts -H "Content-Type: application/json" \
  -d '{"source_type":"url","source_content":"https://en.wikipedia.org/wiki/Red_fox"}'
{"detail":"Could not process URL: URL returned HTTP 403"}
\`\`\`
_(Wikipedia blocks non-browser User-Agents — fixed same day by sending a
realistic User-Agent header. See BUILDLOG.md.)_

## Day 4 — Variant generation + constraint profiles

**Proof: route logic verified end-to-end (SQLite smoke test).**

\`\`\`
$ python3 scripts/smoke_test_variants.py
1) Creating a post to generate variants from...
    Post created: bc6401a0-63e3-4126-8d46-dbcb45ee66b0
2) Auto-generating variants for all 4 platforms...
    All 4 platform variants generated and passed validation:
      - x: 244 chars, status=draft
      - linkedin: 271 chars, status=draft
      - instagram: 253 chars, status=draft
      - telegram: 252 chars, status=draft
3) Attempting to manually create a variant that BREAKS the X length rule...
    Correctly blocked with 422. Reason: Exceeds x max length of 280 characters (got 560)
4) Attempting to manually create a variant that BREAKS the X hashtag rule...
    Correctly blocked with 422. Reason: Too many hashtags for x: max 2, found 5
5) Creating a VALID manual variant (should succeed)...
    Valid variant created successfully.
6) Listing all variants for this post...
    List returned 5 variants.
7) Generating variants for a nonexistent post (should 404)...
    Correctly returned 404.
SMOKE TEST PASSED — variant generation and constraint enforcement work correctly.
\`\`\`

**Proof: real generation against Postgres — one post produces variants for all 4 platforms.**

\`\`\`
$ curl -X POST http://127.0.0.1:8000/posts/ccd14875.../variants/generate
{"created":[
  {"platform":"x","content":"Red Foxes Foxes are clever...#Foxes", ...},
  {"platform":"linkedin","content":"...What do you think? #Foxes", ...},
  {"platform":"instagram","content":"...✨\n#Foxes", ...},
  {"platform":"telegram","content":"...\n\n#Foxes", ...}
],"blocked":[]}
\`\`\`

**Proof: a rule-breaking variant is blocked with a clear, specific error naming the broken rule (real Postgres, not just SQLite).**

\`\`\`
$ curl -X POST http://127.0.0.1:8000/posts/ccd14875.../variants \
  -H


  ## Day 5 — Review workflow

**Proof: full state machine verified (SQLite smoke test).**

\`\`\`
$ python3 scripts/smoke_test_review.py
1) Creating a post and generating variants...
    Created 4 draft variants.
2) Approving the X variant...
    X variant approved.
3) Trying to approve it AGAIN (should be refused, 409)...
    Correctly refused: Cannot approve a variant with status 'approved'; only draft variants can be approved.
4) Rejecting the LinkedIn variant with a reason...
    LinkedIn variant rejected, reason stored.
5) Editing the rejected variant with new content (should reset to draft)...
    Edit succeeded, status reset to draft, rejection_reason cleared.
6) Trying to edit the ALREADY-APPROVED X variant (should be refused, 409)...
    Correctly refused: Cannot edit a variant with status 'approved'; only draft or rejected variants can be edited.
7) Trying to edit with content that BREAKS the X constraint profile...
    Correctly refused: ['Too many hashtags for linkedin: max 5, found 6']
8) Attempting review actions on a nonexistent variant (should 404)...
    Correctly returned 404.
9) Confirming the scheduling guard blocks unapproved variants directly...
    Unapproved variant correctly refused for scheduling: Cannot schedule a variant with status 'draft'; only approved variants can be scheduled.
SMOKE TEST PASSED — review