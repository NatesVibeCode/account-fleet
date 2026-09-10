"""Strict input boundary for JSON, JSONL, and CSV records."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .models import InputItem


class InputDataError(ValueError):
    pass


def load_input_items(
    path: str | Path,
    id_column: Optional[str] = None,
    text_column: Optional[str] = None,
    title_column: Optional[str] = None,
    uri_column: Optional[str] = None,
) -> list[InputItem]:
    source = Path(path)
    if not source.is_file():
        raise InputDataError(f"input file not found: {source}")

    raw_items: object
    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        rows: list[object] = []
        for line_number, line in enumerate(source.read_text().splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise InputDataError(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
        raw_items = rows
    elif suffix == ".json":
        try:
            raw_items = json.loads(source.read_text())
        except json.JSONDecodeError as exc:
            raise InputDataError(f"invalid JSON: {exc.msg}") from exc
        if isinstance(raw_items, dict) and set(raw_items) == {"items"}:
            raw_items = raw_items["items"]
    elif suffix == ".csv":
        try:
            with open(source, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise InputDataError("CSV file has no header columns")
                fieldnames = list(reader.fieldnames)
                
                # Resolve ID column
                resolved_id_col = id_column
                if not resolved_id_col:
                    for candidate in ("item_id", "id", "domain", "key", "name", "slug"):
                        if candidate in fieldnames:
                            resolved_id_col = candidate
                            break
                    if not resolved_id_col:
                        resolved_id_col = fieldnames[0]
                elif resolved_id_col not in fieldnames:
                    raise InputDataError(f"Specified id column '{resolved_id_col}' not found in CSV columns: {fieldnames}")

                # Resolve text column
                resolved_text_col = text_column
                if not resolved_text_col:
                    for candidate in ("text", "research", "content", "body", "description", "summary", "input"):
                        if candidate in fieldnames:
                            resolved_text_col = candidate
                            break
                    if not resolved_text_col:
                        non_id = [col for col in fieldnames if col != resolved_id_col]
                        if non_id:
                            resolved_text_col = non_id[0]
                        else:
                            raise InputDataError(f"CSV requires a text column; found only '{fieldnames[0]}'")
                elif resolved_text_col not in fieldnames:
                    raise InputDataError(f"Specified text column '{resolved_text_col}' not found in CSV columns: {fieldnames}")

                resolved_title_col = title_column if title_column in fieldnames else ("title" if "title" in fieldnames else None)
                resolved_uri_col = uri_column if uri_column in fieldnames else ("source_uri" if "source_uri" in fieldnames else ("url" if "url" in fieldnames else None))

                rows = []
                for row_idx, row in enumerate(reader, start=1):
                    raw_id = (row.get(resolved_id_col) or "").strip()
                    if not raw_id:
                        raise InputDataError(f"CSV row {row_idx} has empty ID column '{resolved_id_col}'")
                    cleaned_id = raw_id.replace(" ", "_").replace("/", "_").replace(":", "_")
                    
                    raw_text = (row.get(resolved_text_col) or "").strip()
                    if not raw_text:
                        continue
                    
                    title = row.get(resolved_title_col) if resolved_title_col else None
                    uri = row.get(resolved_uri_col) if resolved_uri_col else None
                    
                    meta = {
                        k: v for k, v in row.items()
                        if k not in (resolved_id_col, resolved_text_col, resolved_title_col, resolved_uri_col)
                        and v is not None and v != ""
                    }
                    rows.append({
                        "item_id": cleaned_id,
                        "text": raw_text,
                        "title": title or None,
                        "source_uri": uri or None,
                        "metadata": meta,
                    })
                raw_items = rows
        except Exception as exc:
            if isinstance(exc, InputDataError):
                raise
            raise InputDataError(f"failed to parse CSV: {exc}") from exc
    else:
        raise InputDataError("input must use .json, .jsonl, or .csv")

    if not isinstance(raw_items, list):
        raise InputDataError("input must be an array, an {items: [...]} object, or JSONL/CSV rows")
    if not raw_items:
        raise InputDataError("input contains no items")

    items: list[InputItem] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(raw_items):
        try:
            item = InputItem.model_validate(raw_item)
        except ValidationError as exc:
            raise InputDataError(f"invalid item {index}: {exc.errors(include_url=False)}") from exc
        if item.item_id in seen:
            raise InputDataError(f"duplicate item_id: {item.item_id}")
        seen.add(item.item_id)
        items.append(item)
    return items
