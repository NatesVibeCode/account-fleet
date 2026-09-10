"""Strict input boundary for JSON and JSONL records."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import InputItem


class InputDataError(ValueError):
    pass


def load_input_items(path: str | Path) -> list[InputItem]:
    source = Path(path)
    if not source.is_file():
        raise InputDataError(f"input file not found: {source}")

    raw_items: object
    if source.suffix.lower() == ".jsonl":
        rows: list[object] = []
        for line_number, line in enumerate(source.read_text().splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise InputDataError(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
        raw_items = rows
    elif source.suffix.lower() == ".json":
        try:
            raw_items = json.loads(source.read_text())
        except json.JSONDecodeError as exc:
            raise InputDataError(f"invalid JSON: {exc.msg}") from exc
        if isinstance(raw_items, dict) and set(raw_items) == {"items"}:
            raw_items = raw_items["items"]
    else:
        raise InputDataError("input must use .json or .jsonl")

    if not isinstance(raw_items, list):
        raise InputDataError("input must be an array, an {items: [...]} object, or JSONL")
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
