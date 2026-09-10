from bulk_lanes.grounding import verify_grounding

def test_grounding_valid():
    raw_cards = [{
        "item_id": "item_1",
        "slices": [{"slice_id": "full", "text": "Acme Metrics provides real-time latency monitoring for cloud microservices."}]
    }]
    extracted = [{
        "item_id": "item_1",
        "summary": "Cloud latency monitoring",
        "quotes": ["real-time latency monitoring for cloud microservices."]
    }]
    ok, err = verify_grounding(extracted, raw_cards, quote_field="quotes", min_quote_chars=15)
    assert ok is True
    assert err is None

def test_grounding_rejects_hallucination():
    raw_cards = [{
        "item_id": "item_1",
        "slices": [{"slice_id": "full", "text": "Acme Metrics provides real-time latency monitoring."}]
    }]
    extracted = [{
        "item_id": "item_1",
        "summary": "Fraud detection",
        "quotes": ["Acme provides advanced machine learning fraud detection systems."]
    }]
    ok, err = verify_grounding(extracted, raw_cards, quote_field="quotes", min_quote_chars=15)
    assert ok is False
    assert "not found verbatim" in err

def test_grounding_rejects_too_short_quote():
    raw_cards = [{
        "item_id": "item_1",
        "slices": [{"slice_id": "full", "text": "Acme Metrics provides latency monitoring."}]
    }]
    extracted = [{
        "item_id": "item_1",
        "summary": "Monitoring",
        "quotes": ["Acme"]
    }]
    ok, err = verify_grounding(extracted, raw_cards, quote_field="quotes", min_quote_chars=15)
    assert ok is False
    assert "quote too short" in err
