# Social Media Studio

Platform for social media content management

Turn one blog post into a scheduled, multi-platform social campaign. Generates a
platform-specific variant per target, gates every post behind human approval, and
publishes through a durable, idempotent scheduler — a retry or a crash never
produces a duplicate post.

> **Status:** Day 1 of 12 — environment and skeleton only. This README will grow
> each day as features are added.

## Architecture

_Diagram added Day 12._

## Tech stack

- **API:** FastAPI (Python 3.12+)
- **Database:** PostgreSQL
- **Background jobs:** Celery + Redis
- **Real publish targets:** Telegram, LinkedIn
- **Mock publish targets:** X (mock), Instagram (mock)

## Setup (local development)

### Prerequisites
- Docker + Docker Compose
- Python 3.12+

### Steps

\`\`\`bash
# 1. Clone the repo
git clone <your-repo-url>
cd social-media-studio

# 2. Copy environment template and adjust if needed
cp .env.example .env

# 3. Start Postgres + Redis
docker compose up -d

# 4. Create a virtual environment and install dependencies
python -m venv .venv

# Activate it:
#   macOS/Linux:        source .venv/bin/activate
#   Windows Git Bash:   source .venv/Scripts/activate
#   Windows cmd.exe:    .venv\\Scripts\\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Run the API
uvicorn app.main:app --reload
\`\`\`

Visit \`http://127.0.0.1:8000/docs\` for the interactive API explorer.
Visit \`http://127.0.0.1:8000/health\` to confirm the service is up.

## Limitations (Day 1)

- No database tables yet (Day 2).
- No business logic yet — this is infrastructure only.
- FastAPI app currently runs outside Docker (connects to Dockerized Postgres/Redis).
  This may be containerized later if needed for deployment.
