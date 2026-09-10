"""Mathematical grounding verification for model extractions."""
from typing import Any, Dict, List, Optional, Tuple

class GroundingError(ValueError):
    pass

def verify_grounding(
    extracted_items: List[Dict[str, Any]],
    raw_cards: List[Dict[str, Any]],
    quote_field: str = "quotes",
    min_quote_chars: int = 15
) -> Tuple[bool, Optional[str]]:
    """Verifies that all extracted items cite exact substrings from the provided input slices.
    
    Args:
        extracted_items: List of dicts returned by the LLM (must contain 'item_id')
        raw_cards: Original input card dictionaries with 'item_id' and 'slices'
        quote_field: Name of the key containing citations/quotes (string or list of strings/objects)
        min_quote_chars: Minimum character length for each quote
    """
    card_map = {c["item_id"]: c for c in raw_cards}
    seen_ids = set()

    for item in extracted_items:
        iid = item.get("item_id")
        if not iid:
            return False, "Missing 'item_id' in extracted record."
        if iid not in card_map:
            return False, f"Unknown item_id '{iid}' returned by model."
        if iid in seen_ids:
            return False, f"Duplicate item_id '{iid}' returned by model."
        seen_ids.add(iid)

        card = card_map[iid]
        full_slices_text = " ".join(s["text"] for s in card.get("slices", []))

        # Extract quotes to verify
        quotes_to_check = []
        raw_quotes = item.get(quote_field, [])
        if isinstance(raw_quotes, str):
            raw_quotes = [raw_quotes]
        elif isinstance(raw_quotes, list):
            for q in raw_quotes:
                if isinstance(q, str):
                    quotes_to_check.append(q)
                elif isinstance(q, dict) and "quote" in q:
                    quotes_to_check.append(q["quote"])
        
        if not quotes_to_check:
            return False, f"Item '{iid}' did not provide any supporting quotes in field '{quote_field}'."

        for quote in quotes_to_check:
            quote = quote.strip()
            if len(quote) < min_quote_chars:
                return False, f"Item '{iid}' quote too short ({len(quote)} < {min_quote_chars} chars): '{quote}'"
            if quote not in full_slices_text:
                preview = (quote[:60] + "...") if len(quote) > 60 else quote
                return False, f"Item '{iid}' quote not found verbatim in source text: '{preview}'"

    if seen_ids != set(card_map.keys()):
        missing = set(card_map.keys()) - seen_ids
        return False, f"Model missed items from batch: {missing}"

    return True, None
