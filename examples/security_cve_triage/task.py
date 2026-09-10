from bulk_lanes import Task

class CveTriageTask(Task):
    name = "security_cve_triage"
    description = "Screens vulnerability advisories for affected versions, attack vector, and patch availability."
    batch_size = 3
    min_quote_chars = 15
    quote_field = "evidence_quotes"

    system_prompt = (
        "You are an air-gapped vulnerability triage analyst. "
        "Extract vulnerability parameters strictly from the supplied advisory text. "
        "Every extracted finding MUST include an exact verbatim quote from the advisory."
    )

    user_prompt_template = """
Analyze the vulnerability advisories and return JSON matching this schema:
{
  "items": [
    {
      "item_id": "<id>",
      "attack_vector": "network | local | physical | adjacent",
      "severity": "critical | high | medium | low",
      "has_patch": true | false,
      "summary": "<one sentence vulnerability summary>",
      "evidence_quotes": ["<verbatim quote from advisory text>"]
    }
  ]
}

Advisories:
{items_json}
"""
