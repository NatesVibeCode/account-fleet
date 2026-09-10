import pytest
from bulk_lanes.slicer import slice_document

def test_slice_short_document():
    text = "Short text under 6000 chars."
    slices = slice_document(text, max_chars=100)
    assert len(slices) == 1
    assert slices[0]["slice_id"] == "full"
    assert slices[0]["partial"] is False
    assert slices[0]["text"] == text
    assert slices[0]["start"] == 0
    assert slices[0]["end"] == len(text)

def test_slice_long_document_offsets():
    text = "A" * 500 + "B" * 500 + "C" * 500
    slices = slice_document(text, max_chars=300)
    assert len(slices) == 3
    assert [s["slice_id"] for s in slices] == ["head", "mid", "tail"]
    assert all(s["partial"] for s in slices)
    for s in slices:
        # Check slice bounds match actual substring
        assert text[s["start"]:s["end"]] == s["text"]
