"""Exact source-offset grounding verification."""
from typing import Any

from pydantic import ValidationError

from .models import CandidateExtractedItem, ExtractedItem, QuoteRef

class GroundingError(ValueError):
    pass


def normalize_grounding(
    extracted_items: list[CandidateExtractedItem | dict[str, Any]],
    raw_cards: list[dict[str, Any]],
    min_quote_chars: int = 15,
) -> tuple[list[ExtractedItem] | None, str | None]:
    """Resolve unique quote text to canonical absolute offsets, then verify it."""
    card_map = {str(card["item_id"]): card for card in raw_cards}
    normalized: list[ExtractedItem] = []

    for raw_item in extracted_items:
        try:
            item = raw_item if isinstance(raw_item, CandidateExtractedItem) else CandidateExtractedItem.model_validate(raw_item)
        except ValidationError as exc:
            return None, f"Invalid extracted item: {exc.errors(include_url=False)}"
        card = card_map.get(item.item_id)
        if card is None:
            return None, f"Unknown item_id '{item.item_id}' returned by model."
        slices = {str(part["slice_id"]): part for part in card.get("slices", [])}
        quotes: list[QuoteRef] = []
        for candidate in item.quotes:
            if len(candidate.text) < min_quote_chars:
                return None, f"Item '{item.item_id}' quote too short ({len(candidate.text)} < {min_quote_chars} chars): '{candidate.text}'"
            source_slice = slices.get(candidate.slice_id)
            if source_slice is None:
                return None, f"Item '{item.item_id}' references unknown slice '{candidate.slice_id}'."

            if candidate.start is not None and candidate.end is not None:
                start, end = candidate.start, candidate.end
            else:
                slice_text = source_slice.get("text", "")
                first = slice_text.find(candidate.text)
                if first < 0:
                    return None, f"Item '{item.item_id}' quote not found in slice '{candidate.slice_id}'."
                if slice_text.find(candidate.text, first + 1) >= 0:
                    return None, f"Item '{item.item_id}' quote is ambiguous in slice '{candidate.slice_id}'; provide exact offsets."
                start = int(source_slice["start"]) + first
                end = start + len(candidate.text)

            quotes.append(QuoteRef(slice_id=candidate.slice_id, start=start, end=end, text=candidate.text))
        normalized.append(ExtractedItem(
            item_id=item.item_id,
            source_uri=card.get("source_uri"),
            source_digest=card["source_digest"],
            content_type=card["content_type"],
            claims=item.claims,
            quotes=quotes,
        ))

    ok, error = verify_grounding(normalized, raw_cards, min_quote_chars=min_quote_chars)
    return (normalized, None) if ok else (None, error)

def verify_grounding(
    extracted_items: list[ExtractedItem | dict[str, Any]],
    raw_cards: list[dict[str, Any]],
    quote_field: str = "quotes",
    min_quote_chars: int = 15,
) -> tuple[bool, str | None]:
    """Require each quote to match one supplied slice at its absolute offsets."""
    if quote_field != "quotes":
        return False, "typed output requires the canonical 'quotes' field"

    card_map = {str(card["item_id"]): card for card in raw_cards}
    seen_ids: set[str] = set()
    seen_order: list[str] = []

    for raw_item in extracted_items:
        try:
            item = raw_item if isinstance(raw_item, ExtractedItem) else ExtractedItem.model_validate(raw_item)
        except ValidationError as exc:
            return False, f"Invalid extracted item: {exc.errors(include_url=False)}"

        if item.item_id not in card_map:
            return False, f"Unknown item_id '{item.item_id}' returned by model."
        if item.item_id in seen_ids:
            return False, f"Duplicate item_id '{item.item_id}' returned by model."
        seen_ids.add(item.item_id)
        seen_order.append(item.item_id)

        card = card_map[item.item_id]
        if item.source_digest != card.get("source_digest"):
            return False, f"Item '{item.item_id}' source digest does not match the supplied source."
        if item.source_uri != card.get("source_uri") or item.content_type != card.get("content_type"):
            return False, f"Item '{item.item_id}' source metadata does not match the supplied source."
        slices = {str(part["slice_id"]): part for part in card.get("slices", [])}
        for quote in item.quotes:
            if len(quote.text) < min_quote_chars:
                return False, f"Item '{item.item_id}' quote too short ({len(quote.text)} < {min_quote_chars} chars): '{quote.text}'"
            source_slice = slices.get(quote.slice_id)
            if source_slice is None:
                return False, f"Item '{item.item_id}' references unknown slice '{quote.slice_id}'."

            slice_start = source_slice.get("start")
            slice_end = source_slice.get("end")
            if not isinstance(slice_start, int) or not isinstance(slice_end, int):
                return False, f"Item '{item.item_id}' source slice has invalid bounds."
            if quote.start < slice_start or quote.end > slice_end:
                return False, f"Item '{item.item_id}' quote bounds fall outside slice '{quote.slice_id}'."

            relative_start = quote.start - slice_start
            relative_end = quote.end - slice_start
            if source_slice.get("text", "")[relative_start:relative_end] != quote.text:
                return False, f"Item '{item.item_id}' quote does not exactly match its source offsets."

    missing = set(card_map) - seen_ids
    if missing:
        return False, f"Model missed items from batch: {sorted(missing)}"
    if seen_order != list(card_map):
        return False, "Model output order does not match input order."
    return True, None
