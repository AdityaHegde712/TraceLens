"""OpenRouter free model discovery and parameter count parsing."""

import logging
import re
from typing import Any

import httpx

from tracelens.config import get_settings

logger = logging.getLogger(__name__)

PARAM_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:billion|b)\b", re.IGNORECASE)


def parse_parameter_count(*texts: str) -> str | None:
    """Extract estimated parameter count from model name, description, or id.

    Args:
        *texts: String candidates to inspect.

    Returns:
        Formatted string like '118B', '70B', or None if not found.
    """
    for text in texts:
        if not text:
            continue
        match = PARAM_PATTERN.search(text)
        if match:
            num = match.group(1)
            num = num.removesuffix(".0")
            return f"{num}B"
    return None


def discover_free_models(api_key: str | None = None) -> list[dict[str, Any]]:
    """Discover free-tier models from OpenRouter with metadata.

    Args:
        api_key: Optional OpenRouter API key. If not passed, uses settings.OPENROUTER_API_KEY.

    Returns:
        List of dicts containing id, name, context_length, params, and description.
    """
    settings = get_settings()
    key = api_key if api_key is not None else settings.OPENROUTER_API_KEY

    headers: dict[str, str] = {
        "HTTP-Referer": "https://github.com/aditya-hegde/tracelens",
        "X-Title": "TraceLens",
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        url = "https://openrouter.ai/api/v1/models"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json().get("data", [])

        free_models = []
        for m in data:
            model_id = m.get("id", "")
            if ":free" in model_id.lower() or m.get("pricing", {}).get("prompt") == "0":
                desc = m.get("description", "")
                name = m.get("name", model_id)
                params = parse_parameter_count(model_id, name, desc)
                free_models.append({
                    "id": model_id,
                    "name": name,
                    "context_length": m.get("context_length", 0),
                    "params": params,
                    "description": desc,
                })
        if free_models:
            return free_models
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("Failed to discover free models from OpenRouter: %s", exc)

    # Fallback to configured canonical tiers
    return [
        {
            "id": settings.TIER_MODELS["cloud_large"],
            "name": f"Cloud Large ({settings.TIER_MODELS['cloud_large']})",
            "context_length": 32768,
            "params": parse_parameter_count(settings.TIER_MODELS["cloud_large"], "118B"),
            "description": "Configured cloud large tier model",
        },
        {
            "id": settings.TIER_MODELS["cloud_frontier"],
            "name": f"Cloud Frontier ({settings.TIER_MODELS['cloud_frontier']})",
            "context_length": 65536,
            "params": parse_parameter_count(settings.TIER_MODELS["cloud_frontier"], "975B"),
            "description": "Configured cloud frontier tier model",
        },
        {
            "id": settings.TIER_MODELS["local_small"],
            "name": f"Local Small ({settings.TIER_MODELS['local_small']})",
            "context_length": 8192,
            "params": parse_parameter_count(settings.TIER_MODELS["local_small"], "3B"),
            "description": "Configured local Ollama model",
        },
        {
            "id": settings.TIER_MODELS["local_mid"],
            "name": f"Local Mid ({settings.TIER_MODELS['local_mid']})",
            "context_length": 32768,
            "params": parse_parameter_count(settings.TIER_MODELS["local_mid"], "7B"),
            "description": "Configured local mid-tier model",
        },
    ]
