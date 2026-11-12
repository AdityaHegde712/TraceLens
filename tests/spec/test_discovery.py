"""Specification tests for OpenRouter dynamic free model discovery and parameter parsing.

Strict TDD suite locking behavior for:
1. Fetching models from OpenRouter /api/v1/models.
2. Filtering for free tier (:free).
3. Parsing model metadata: id, name, context_length, parameter count.
4. Graceful fallback on network failure or empty response.
"""

from unittest.mock import MagicMock, patch

import httpx

from tracelens.discovery import (
    discover_free_models,
    parse_parameter_count,
)


class TestDiscovery:
    """Locked assertions for free model discovery and parameter count parsing."""

    def test_parse_parameter_count(self):
        assert parse_parameter_count("poolside/laguna-s-2.1:free", "A 118B parameter reasoning model") == "118B"
        assert parse_parameter_count("meta-llama/llama-3.3-70b-instruct:free", "") == "70B"
        assert parse_parameter_count("thinkingmachines/inkling:free", "Massive MoE with 975 billion parameters") == "975B"
        assert parse_parameter_count("qwen/qwen-2.5-7b-chat:free", "7B dense LLM") == "7B"
        assert parse_parameter_count("custom/unknown-model:free", "No parameter count specified") is None

    def test_discover_free_models_success(self):
        mock_data = {
            "data": [
                {
                    "id": "poolside/laguna-s-2.1:free",
                    "name": "Poolside: Laguna S 2.1 (free)",
                    "description": "118B parameter coding model",
                    "context_length": 32768,
                },
                {
                    "id": "meta-llama/llama-3.3-70b-instruct:free",
                    "name": "Meta: Llama 3.3 70B Instruct (free)",
                    "description": "Meta Llama 3.3 70B",
                    "context_length": 131072,
                },
                {
                    "id": "openai/gpt-4o",
                    "name": "OpenAI: GPT-4o",
                    "description": "Paid model",
                    "context_length": 128000,
                },
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
            models = discover_free_models(api_key="sk-test")
            assert len(models) == 2
            ids = [m["id"] for m in models]
            assert "poolside/laguna-s-2.1:free" in ids
            assert "meta-llama/llama-3.3-70b-instruct:free" in ids
            assert "openai/gpt-4o" not in ids

            laguna = next(m for m in models if m["id"] == "poolside/laguna-s-2.1:free")
            assert laguna["params"] == "118B"
            assert laguna["context_length"] == 32768

            # Verify request
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "openrouter.ai/api/v1/models" in args[0]
            assert kwargs["headers"]["Authorization"] == "Bearer sk-test"

    def test_discover_free_models_fallback_on_network_error(self):
        with patch("httpx.Client.get", side_effect=httpx.ConnectError("Network unreachable")):
            models = discover_free_models()
            assert isinstance(models, list)
            assert len(models) >= 1  # Should return fallback tiers
            assert any("laguna" in m["id"] or "free" in m["id"] for m in models)
