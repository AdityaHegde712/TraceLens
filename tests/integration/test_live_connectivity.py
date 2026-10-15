"""Integration test verifying live connectivity to OpenRouter endpoints."""

import pytest

from tracelens.agent.llm_backend import OpenAIBackend
from tracelens.config import get_settings


@pytest.mark.live
def test_openrouter_live_ping():
    """Verify live connectivity and ping response from OpenRouter."""
    settings = get_settings()
    has_key = bool(settings.OPENROUTER_API_KEY)
    print(f"\n[Live Connectivity] OPENROUTER_API_KEY present: {has_key}")

    if not has_key:
        pytest.skip("OPENROUTER_API_KEY not configured in environment")

    # Use MODEL_1 or default model from settings
    target_model = settings.MODEL_1 or settings.OPENROUTER_MODEL_DEFAULT
    print(f"[Live Connectivity] Querying model: {target_model}")

    backend = OpenAIBackend(model=target_model)
    response = backend.generate(prompt="Respond with exactly: PING_OK")
    print(f"[Live Connectivity] Model response: {response.strip()}")

    assert len(response.strip()) > 0
