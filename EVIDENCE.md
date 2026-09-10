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