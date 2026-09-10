from bulk_lanes import Task

class SaasIntelligenceTask(Task):
    name = "saas_intelligence"
    description = "Extracts product pricing, API support, and developer features from SaaS homepages."
    batch_size = 4
    min_quote_chars = 15
    quote_field = "evidence_quotes"

    system_prompt = (
        "You are an air-gapped market intelligence screener. "
        "Analyze the provided software product pages. "
        "Extract pricing model, API/SDK support, and core value proposition. "
        "Every claim MUST provide an exact verbatim quote from the supplied text. "
        "Never guess or fabricate quotes."
    )

    user_prompt_template = """
Extract SaaS capabilities for each company. Return valid JSON:
{
  "items": [
    {
      "item_id": "<id>",
      "pricing_type": "free_tier | usage_based | enterprise_only | unknown",
      "has_api": true | false,
      "supported_sdks": ["<language>", ...],
      "core_value_prop": "<one sentence>",
      "evidence_quotes": ["<exact quote from text>"]
    }
  ]
}

Input items:
{items_json}
"""
