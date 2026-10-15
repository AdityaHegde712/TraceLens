"""LLM Backend adapters for TraceLens agent reasoning.

Provides an abstract interface and concrete implementations for Mock testing,
local Ollama instances, and OpenAI-compatible inference APIs.
"""

from abc import ABC, abstractmethod
from typing import Any
import httpx


class LLMBackend(ABC):
    """Abstract base class for language model inference backends."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate text from a prompt and optional system instructions.

        Args:
            prompt: User prompt or scratchpad context.
            system_prompt: System-level role and formatting instructions.

        Returns:
            Generated response string.
        """
        pass


class MockLLMBackend(LLMBackend):
    """Deterministic mock backend for unit tests and reproducible benchmarks."""

    def __init__(
        self,
        default_response: str = "Analysis complete.",
        responses: list[str] | None = None,
    ) -> None:
        """Initialize mock backend with configured responses.

        Args:
            default_response: Fallback response string when responses list is empty.
            responses: Optional ordered queue of responses to return sequentially.
        """
        self.default_response = default_response
        self.responses = list(responses) if responses is not None else []
        self.history: list[dict[str, str]] = []
        self._last_response: str | None = None

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Record call and return the next programmed response."""
        self.history.append({"prompt": prompt, "system_prompt": system_prompt})
        if self.responses:
            self._last_response = self.responses.pop(0)
            return self._last_response
        if self._last_response is not None and self.default_response == "Analysis complete.":
            return self._last_response
        return self.default_response


class OllamaBackend(LLMBackend):
    """Local inference backend powered by Ollama."""

    def __init__(
        self,
        model: str = "llama3:8b",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
    ) -> None:
        """Initialize Ollama connection parameters."""
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Query local Ollama instance via HTTP POST /api/generate."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self.base_url}/api/generate"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("response", ""))


class OpenAIBackend(LLMBackend):
    """OpenAI-compatible inference backend (supports OpenAI, vLLM, DeepSeek, etc.)."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
    ) -> None:
        """Initialize OpenAI connection parameters."""
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Query OpenAI-compatible endpoint via HTTP POST /chat/completions."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                url,
                headers=headers,
                json={"model": self.model, "messages": messages},
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices and "message" in choices[0]:
                return str(choices[0]["message"].get("content", ""))
            return ""
