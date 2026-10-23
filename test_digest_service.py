from digest_service import PaymentEvent, summarize


def test_summary_flags_only_risk_sensitive_payments():
    events = [PaymentEvent("Aster", 1000, 69), PaymentEvent("Beacon", 2500, 70)]
    assert summarize(events) == {
        "payment_count": 2,
        "total_cents": 3500,
        "flagged_merchants": ["Beacon"],
    }
