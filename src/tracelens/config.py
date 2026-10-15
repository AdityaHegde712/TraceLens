"""Central configuration catalog and environment loader for TraceLens.

Provides normalized endpoint URLs, API credentials, and tiered model slugs
supporting local Ollama models and remote OpenRouter cloud frontiers.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load .env file from the current working directory or project root
_env_path = Path(".env")
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)
else:
    load_dotenv(override=False)


class Settings:
    """Normalized runtime configuration parameters."""

    def __init__(self) -> None:
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.OLLAMA_MODEL_DEFAULT = os.getenv("OLLAMA_MODEL_DEFAULT", "llama3.2:3b")
        self.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
        self.OPENROUTER_BASE_URL = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
        self.OPENROUTER_MODEL_DEFAULT = os.getenv(
            "OPENROUTER_MODEL_DEFAULT", "openrouter/free"
        )
        self.MODEL_1 = os.getenv("MODEL_1", "poolside/laguna-s-2.1:free")
        self.MODEL_2 = os.getenv("MODEL_2", "thinkingmachines/inkling:free")
        self.TRACELENS_HOST = os.getenv("TRACELENS_HOST", "127.0.0.1")
        self.TRACELENS_PORT = int(os.getenv("TRACELENS_PORT", "8000"))

    @property
    def TIER_MODELS(self) -> dict[str, str]:
        """Mapping from normalized tier names to specific model identifiers."""
        return {
            "local_small": self.OLLAMA_MODEL_DEFAULT,
            "local_mid": os.getenv("MODEL_LOCAL_MID", "qwen2.5:7b"),
            "cloud_large": self.MODEL_1,
            "cloud_frontier": self.MODEL_2,
        }


def get_settings() -> Settings:
    """Retrieve an instantiated Settings object."""
    return Settings()


# Module-level defaults for direct access
_active = get_settings()
OLLAMA_BASE_URL = _active.OLLAMA_BASE_URL
OLLAMA_MODEL_DEFAULT = _active.OLLAMA_MODEL_DEFAULT
OPENROUTER_API_KEY = _active.OPENROUTER_API_KEY
OPENROUTER_BASE_URL = _active.OPENROUTER_BASE_URL
TIER_MODELS = _active.TIER_MODELS
