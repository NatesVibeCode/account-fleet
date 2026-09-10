import json
import httpx
from free_fleet.providers.openai_compatible import OpenAICompatibleProvider
from free_fleet.providers.registry import ProviderRegistry


def test_provider_registry_resolution():
    registry = ProviderRegistry()
    assert registry.get("opencode").__class__.__name__ == "OpenCodeProvider"
    assert registry.get("openrouter").__class__.__name__ == "OpenRouterProvider"
    assert registry.get("ollama").__class__.__name__ == "OpenAICompatibleProvider"
    assert registry.get("lmstudio").__class__.__name__ == "OpenAICompatibleProvider"

    # Resolution by provider hint
    assert registry.resolve("ollama", "my-model").__class__.__name__ == "OpenAICompatibleProvider"
    # Resolution by route prefix
    assert registry.resolve(None, "vllm/llama-3").__class__.__name__ == "OpenAICompatibleProvider"
    assert registry.resolve(None, "ollama:llama3.2:latest").__class__.__name__ == "OpenAICompatibleProvider"
    assert registry.resolve(None, "openrouter/free").__class__.__name__ == "OpenRouterProvider"
    assert registry.resolve(None, "openrouter:free").__class__.__name__ == "OpenRouterProvider"


def test_openai_compatible_successful_completion(monkeypatch):
    def mock_post(url, headers, json):
        resp_data = {
            "choices": [{"message": {"content": '{"items": []}'}}],
            "usage": {"total_tokens": 42},
            "cost": 0.0,
        }
        return httpx.Response(200, json=resp_data)

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, headers, json: mock_post(url, headers, json))

    prov = OpenAICompatibleProvider(base_url="http://localhost:11434/v1")
    ok, text, receipt = prov.run_prompt("ollama/qwen", "hello")
    assert ok is True
    assert text == '{"items": []}'
    assert receipt["status"] == "complete"
    assert receipt["cost_status"] == "reported_zero"
    assert receipt["usage"]["total_tokens"] == 42


def test_openai_compatible_rate_limit_429(monkeypatch):
    def mock_429(url, headers, json):
        headers = {"retry-after": "15"}
        return httpx.Response(429, headers=headers, text="Rate limit exceeded")

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, headers, json: mock_429(url, headers, json))

    prov = OpenAICompatibleProvider(base_url="http://localhost:11434/v1")
    ok, text, receipt = prov.run_prompt("ollama/qwen", "hello")
    assert ok is False
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "rate_limit"
    assert receipt["retry_after"] == 15.0


def test_openai_compatible_transient_503(monkeypatch):
    def mock_503(url, headers, json):
        return httpx.Response(503, text="Service Unavailable")

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, headers, json: mock_503(url, headers, json))

    prov = OpenAICompatibleProvider(base_url="http://localhost:11434/v1")
    ok, text, receipt = prov.run_prompt("ollama/qwen", "hello")
    assert ok is False
    assert receipt["error_type"] == "transient_http"
    assert receipt["retry_after"] == 5.0


def test_openai_compatible_prefix_stripping(monkeypatch):
    captured_model = None

    def mock_post(url, headers, json):
        nonlocal captured_model
        captured_model = json.get("model")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"total_tokens": 5},
            "cost": 0.0,
        })

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, headers, json: mock_post(url, headers, json))

    prov = OpenAICompatibleProvider(base_url="http://localhost:11434/v1")
    prov.run_prompt("ollama/llama3.2:latest", "test")
    assert captured_model == "llama3.2:latest"

    prov.run_prompt("ollama:llama3.2:latest", "test")
    assert captured_model == "llama3.2:latest"
