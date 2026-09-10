# Task contracts

Read this when creating or importing a task.

Prefer a preset:

```bash
bulk-lanes init labels --preset classify
bulk-lanes init facts --preset extract
bulk-lanes init queue --preset triage
bulk-lanes init summaries --preset summarize
```

SQLite stores immutable task revisions and selects one current revision per task name. A supplied TaskSpec JSON is validated and registered before use.

## InputItem

```json
{
  "item_id": "item_1",
  "text": "Required source text",
  "title": "Optional",
  "source_uri": "https://example.com/source",
  "content_type": "text/plain",
  "metadata": {}
}
```

Only `item_id` and `text` are required. The object is closed. Do not substitute `id`, `body`, `content`, or other aliases. Invalid JSONL lines and duplicate IDs are errors.

## TaskSpec

```json
{
  "$schema": "https://raw.githubusercontent.com/NatesVibeCode/bulk-lanes/master/schemas/task-v1.schema.json",
  "format_version": "bulk_lanes_task_v1",
  "name": "product-triage",
  "instructions": "Extract a supported summary and category.",
  "batch_size": 4,
  "max_slice_chars": 6000,
  "min_quote_chars": 15,
  "claims_schema": {
    "type": "object",
    "properties": {
      "summary": {"type": "string"},
      "category": {"enum": ["a", "b", "unknown"]}
    },
    "required": ["summary", "category"],
    "additionalProperties": false
  }
}
```

Put extraction meaning in `instructions`. Put field names, types, enums, required status, and closure in `claims_schema`.

## Model boundary

The model returns `item_id`, `claims`, and `quotes`. Each quote requires `slice_id` and exact `text`; `start` and `end` are optional.

If the text occurs exactly once in that slice, bulk-lanes computes its absolute offsets. If it occurs more than once, the response must include offsets. The stored `ModelOutput` always includes offsets, source URI, content type, and a SHA-256 source digest. The exported packet embeds this exact TaskSpec, binds it to its revision digest, and revalidates every record against `claims_schema` when written or read.

Use `bulk-lanes schema KIND` to inspect the admitted `task`, `input`, `candidate-output`, `output`, `packet`, or `database` contract.
