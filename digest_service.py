"""Schedule and deliver a risk-aware weekly payment digest."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import infrai

QUEUE_NAME = "weekly-payment-digests"


@dataclass(frozen=True)
class PaymentEvent:
    merchant: str
    amount_cents: int
    risk_score: int


def summarize(events: list[PaymentEvent]) -> dict[str, Any]:
    """Keep high-risk payments visible while aggregating the rest."""
    total = sum(event.amount_cents for event in events)
    flagged = [event.merchant for event in events if event.risk_score >= 70]
    return {"payment_count": len(events), "total_cents": total, "flagged_merchants": flagged}


def schedule_digest() -> str:
    webhook = os.environ.get("DIGEST_WEBHOOK_URL", "https://example.com/hooks/weekly-digest")
    result = infrai.cron.create(cron_expr="0 9 * * 1", task=webhook)
    return str(result["job_id"])


def enqueue_digest(events: list[PaymentEvent]) -> dict[str, Any]:
    return infrai.queue.publish(queue=QUEUE_NAME, payload={"kind": "weekly_payment_digest", "summary": summarize(events)})


def consume_one() -> dict[str, Any] | None:
    result = infrai.queue.consume(queue=QUEUE_NAME, max_messages=1, visibility_timeout=60)
    messages = result.get("messages") or []
    if not messages:
        return None
    message = messages[0]
    infrai.queue.ack(queue=QUEUE_NAME, message_id=message["message_id"])
    return message


if __name__ == "__main__":
    events = [PaymentEvent("Northstar Bank", 12500, 18), PaymentEvent("Harbor Exchange", 9800, 82)]
    print("scheduled:", schedule_digest())
    print("queued:", enqueue_digest(events))
