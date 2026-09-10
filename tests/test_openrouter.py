from bulk_lanes.providers.openrouter import OpenRouterProvider


class FakeResponse:
    status_code = 200
    text = ""

    def json(self):
        return {
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, *args, **kwargs):
        return FakeResponse()


def test_free_suffix_does_not_manufacture_zero_cost(monkeypatch):
    monkeypatch.setattr("bulk_lanes.providers.openrouter.httpx.Client", FakeClient)
    ok, _, receipt = OpenRouterProvider(api_key="key").run_prompt("openrouter/example:free", "prompt")
    assert ok is True
    assert receipt["cost"] is None
    assert receipt["cost_status"] == "unknown"
