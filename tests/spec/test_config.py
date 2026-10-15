"""Specification tests for TraceLens Central Configuration and OpenRouter Integration.

Strict TDD suite locking behavior for:
1. Central settings catalog loading environment variables from .env.
2. Normalized model tiers (local_small, local_mid, cloud_large, cloud_frontier).
3. OpenAIBackend fallback to OpenRouter base URL, API key, and referral headers.
"""

from unittest.mock import MagicMock, patch

from tracelens.agent.llm_backend import OpenAIBackend
from tracelens.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL_DEFAULT,
    OPENROUTER_BASE_URL,
    TIER_MODELS,
    Settings,
    get_settings,
)


class TestConfigCatalog:
    """Locked assertions for the central configuration catalog."""

    def test_default_config_values(self):
        settings = get_settings()
        assert settings.OLLAMA_BASE_URL == "http://127.0.0.1:11434"
        assert settings.OLLAMA_MODEL_DEFAULT == "llama3.2:3b"
        assert settings.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"

    def test_tier_models_mapping(self):
        settings = get_settings()
        assert "local_small" in settings.TIER_MODELS
        assert "local_mid" in settings.TIER_MODELS
        assert "cloud_large" in settings.TIER_MODELS
        assert "cloud_frontier" in settings.TIER_MODELS

        assert settings.TIER_MODELS["local_small"] == "llama3.2:3b"
        assert settings.TIER_MODELS["local_mid"] == "qwen2.5:7b"
        assert settings.TIER_MODELS["cloud_large"] == "poolside/laguna-s-2.1:free"
        assert settings.TIER_MODELS["cloud_frontier"] == "thinkingmachines/inkling:free"

    def test_module_level_exports(self):
        assert OLLAMA_BASE_URL == "http://127.0.0.1:11434"
        assert OLLAMA_MODEL_DEFAULT == "llama3.2:3b"
        assert OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
        assert TIER_MODELS["local_small"] == "llama3.2:3b"

    def test_custom_env_override(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL_DEFAULT", "custom-llama:latest")
        monkeypatch.setenv("MODEL_1", "custom/large-model:free")

        custom_settings = Settings()
        assert custom_settings.OLLAMA_MODEL_DEFAULT == "custom-llama:latest"
        assert custom_settings.TIER_MODELS["local_small"] == "custom-llama:latest"
        assert custom_settings.TIER_MODELS["cloud_large"] == "custom/large-model:free"


class TestOpenRouterIntegration:
    """Locked assertions for OpenAIBackend OpenRouter compatibility."""

    def test_backend_defaults_to_openrouter_when_empty(self, monkeypatch):
        test_key = "sk-or-v1-mock-test-key-12345"
        monkeypatch.setenv("OPENROUTER_API_KEY", test_key)

        backend = OpenAIBackend()
        assert backend.base_url == "https://openrouter.ai/api/v1"
        assert backend.api_key == test_key

    def test_backend_sends_openrouter_headers(self, monkeypatch):
        test_key = "sk-or-v1-mock-test-key-12345"
        monkeypatch.setenv("OPENROUTER_API_KEY", test_key)

        backend = OpenAIBackend(model="poolside/laguna-s-2.1:free")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Grounded diagnosis from OpenRouter"}}]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            output = backend.generate(prompt="Analyze incident")
            assert output == "Grounded diagnosis from OpenRouter"

            # Check call headers
            call_kwargs = mock_post.call_args[1]
            headers = call_kwargs["headers"]
            assert headers["Authorization"] == f"Bearer {test_key}"
            assert "HTTP-Referer" in headers
            assert "X-Title" in headers
            assert headers["X-Title"] == "TraceLens"
