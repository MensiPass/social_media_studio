"""
LIVE idempotency check: enqueues the SAME publish_slot task TWICE in a row
for a real schedule slot, via your REAL Celery broker (Redis), and reports
how many PublishAttempt rows exist afterward in your REAL Postgres.
Expected: exactly 1, even though publish_slot was enqueued twice.

Prerequisite: a real `celery worker` process must already be running
(see Day 9/10 instructions) — this script only enqueues tasks, it doesn't
run them itself.

Usage:
    python scripts/live_check_idempotency.py <schedule_slot_id>
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tasks.publish_tasks import publish_slot
from app.db.session import SessionLocal
from app.db.models import PublishAttempt


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/live_check_idempotency.py <schedule_slot_id>")
        sys.exit(1)

    slot_id = sys.argv[1]

    print(f"Enqueuing publish_slot for slot {slot_id} TWICE in a row...")
    publish_slot.delay(slot_id)
    publish_slot.delay(slot_id)

    print("Waiting 5 seconds for your worker to process both...")
    time.sleep(5)

    db = SessionLocal()
    attempts = db.query(PublishAttempt).filter_by(schedule_slot_id=slot_id).all()
    db.close()

    print(f"\nPublishAttempt rows found for this slot: {len(attempts)}")
    for a in attempts:
        print(f"  - status={a.status.value}, external_post_id={a.external_post_id}, detail={a.detail}")

    if len(attempts) == 1:
        print("\n Exactly ONE attempt recorded despite TWO publish calls — idempotency confirmed.")
    else:
        print(f"\n Expected 1 attempt, found {len(attempts)} — idempotency check FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()