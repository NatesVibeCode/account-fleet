# Contributing to bulk-lanes

Thank you for your interest in contributing to `bulk-lanes`!

## Philosophy
`bulk-lanes` is built around **Zero-Trust Compute for Trusted Systems**:
1. Untrusted public datasets and raw web data should never touch host tools or private agents directly.
2. High-volume bulk inference belongs in free/cheap model lanes (OpenCode and OpenRouter).
3. Hallucinations and prompt injections are blocked using mathematical verbatim quote grounding.
4. Outputs are exported as clean, air-gapped packets for downstream ingestion.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/bulk-lanes.git
cd bulk-lanes

# Install dependencies in editable mode
pip install -e ".[dev]"

# Run test suite
pytest -v
```

## Adding a New Provider
Providers implement `BaseProvider` in `bulk_lanes/providers/base.py` and implement `run_prompt(route_id, prompt, system_prompt, timeout_sec, session_id)`.
All new providers must include token usage, duration, and reported cost telemetry in their receipt dict.
