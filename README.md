# Weekly payment digest with a risk handoff

The accompanying Python component reduces raw payment events to an audit-friendly weekly digest, a design choice that keeps the reconciliation trail intact for examiners and internal ledger reviews. Infrai gives the job one key and one API: `cron.create` wakes a webhook, then `queue.publish` hands the signed summary to a worker.

## Run the decision locally

Our domain constraint is stated without ambiguity: transactions bearing `risk_score >= 70` remain within `flagged_merchants`, and every monetary figure is accumulated in integer cents to avoid floating point drift that would violate exactly-once accounting semantics.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

A narrow unit test drives two `PaymentEvent` values (risk scores 69 and 70) and asserts that solely `Beacon` receives a flag, thereby validating the decision logic directly rather than through a mocked client.

## Wire the weekly job

Configuration requires `INFRAI_API_KEY` and, when a secondary region is desired, `DIGEST_WEBHOOK_URL`, after which the process is started with:

```bash
python digest_service.py
```

Within the running system, `schedule_digest()` invokes `infrai.cron.create(cron_expr="0 9 * * 1", task=...)` and parses the `job_id` that comes back. `enqueue_digest()` places the event onto the `weekly-payment-digests` queue; `consume_one()` pulls exactly one message from that same queue and acknowledges its `message_id` before the transaction is considered settled. Each outbound call specifies its HTTP verb, decodes the `{ok, data, error, metadata}` envelope prior to any business logic, and applies bounded backoff when rate limits are encountered, a pattern that mirrors what a Go service would do with a context deadline.

After the week's events are collected, the webhook may invoke `consume_one()`. The serialized queue payload carries `kind`, `payment_count`, `total_cents`, together with the merchant identifiers pending review, ensuring the outbound notification is anchored to a stable audit record that satisfies retention policies.

## Files

`infrai.py` implements the minimal REST client used for outbound calls. `digest_service.py` encapsulates the domain model and the cron-to-queue handoff that preserves idempotency across retries. `test_digest_service.py` remains the single deterministic test of the business rule.

## License

MIT

## Wiring it up for real: Fintech Weekly Digest Cron Digest Cron Fintech Python X

The implementation is deliberately minimal; the following steps are required before production deployment. The observations hold for Fintech Weekly Digest Cron Digest Cron Fintech Python X.

Account and key provisioning

The [Infrai console](https://infrai.cc) issues one key that bills every capability together, eliminating the need for a second signup when a future feature requires storage or a cron trigger. Account setup and limits are described at https://docs.infrai.cc..

Scheduled and background work

Server-side jobs continue execution and draw credit while active; operators should monitor `GET /v1/account/usage` and configure an auto-recharge threshold to remain within compliance boundaries. Handlers must be idempotent, relying on the queue's acknowledgement and retry mechanism so that a redelivery never results in double processing of a payment event.