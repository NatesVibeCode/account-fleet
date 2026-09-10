from bulk_lanes.grounding import normalize_grounding, verify_grounding
from bulk_lanes.packer import pack_items


def card(item_id, text, max_chars=6000):
    return pack_items([{"item_id": item_id, "text": text}], max_slice_chars=max_chars)[0]["items"][0]


def extracted(item_id, source_card, claims, quotes):
    return {
        "item_id": item_id,
        "source_uri": source_card["source_uri"],
        "source_digest": source_card["source_digest"],
        "content_type": source_card["content_type"],
        "claims": claims,
        "quotes": quotes,
    }

def test_grounding_valid():
    raw_cards = [card("item_1", "Acme Metrics provides real-time latency monitoring for cloud microservices.")]
    rows = [extracted("item_1", raw_cards[0], {"summary": "Cloud latency monitoring"}, [
        {"slice_id": "full", "start": 22, "end": 75, "text": "real-time latency monitoring for cloud microservices."}
    ])]
    ok, err = verify_grounding(rows, raw_cards, quote_field="quotes", min_quote_chars=15)
    assert ok is True
    assert err is None

def test_grounding_rejects_hallucination():
    raw_cards = [card("item_1", "Acme Metrics provides real-time latency monitoring.")]
    rows = [extracted("item_1", raw_cards[0], {"summary": "Fraud detection"}, [
        {"slice_id": "full", "start": 0, "end": 65, "text": "Acme provides advanced machine learning fraud detection systems."}
    ])]
    ok, err = verify_grounding(rows, raw_cards, quote_field="quotes", min_quote_chars=15)
    assert ok is False
    assert "bounds" in err or "exactly match" in err

def test_grounding_rejects_too_short_quote():
    raw_cards = [card("item_1", "Acme Metrics provides latency monitoring.")]
    rows = [extracted("item_1", raw_cards[0], {"summary": "Monitoring"}, [
        {"slice_id": "full", "start": 0, "end": 4, "text": "Acme"}
    ])]
    ok, err = verify_grounding(rows, raw_cards, quote_field="quotes", min_quote_chars=15)
    assert ok is False
    assert "quote too short" in err


def test_grounding_rejects_quote_spanning_distant_slices():
    source = "A" * 100 + "B" * 100 + "C" * 100
    raw_cards = [card("item_1", source, max_chars=90)]
    rows = [extracted("item_1", raw_cards[0], {"summary": "invalid"}, [
        {"slice_id": "head", "start": 90, "end": 111, "text": "A" * 10 + " " + "B" * 10}
    ])]

    ok, err = verify_grounding(rows, raw_cards, min_quote_chars=15)

    assert ok is False
    assert "bounds" in err or "exactly match" in err


def test_unique_quote_text_gets_deterministic_offsets():
    text = "Before this exact evidence appears after."
    raw_cards = [card("i1", text)]
    items, error = normalize_grounding(
        [{"item_id": "i1", "claims": {}, "quotes": [{"slice_id": "full", "text": "this exact evidence"}]}],
        raw_cards,
        min_quote_chars=5,
    )
    assert error is None
    assert items[0].quotes[0].start == text.index("this exact evidence")
    assert text[items[0].quotes[0].start:items[0].quotes[0].end] == items[0].quotes[0].text


def test_ambiguous_quote_requires_offsets():
    text = "same exact evidence and same exact evidence"
    raw_cards = [card("i1", text)]
    items, error = normalize_grounding(
        [{"item_id": "i1", "claims": {}, "quotes": [{"slice_id": "full", "text": "same exact evidence"}]}],
        raw_cards,
        min_quote_chars=5,
    )
    assert items is None
    assert "ambiguous" in error


def test_output_order_must_match_input_order():
    cards = [card("first", "first source evidence"), card("second", "second source evidence")]
    rows = [
        extracted("second", cards[1], {}, [{"slice_id": "full", "start": 0, "end": 22, "text": "second source evidence"}]),
        extracted("first", cards[0], {}, [{"slice_id": "full", "start": 0, "end": 21, "text": "first source evidence"}]),
    ]
    ok, error = verify_grounding(rows, cards, min_quote_chars=5)
    assert ok is False
    assert "order" in error
