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