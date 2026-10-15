"""Telemetry sanitizer for credential masking and canary token detection.

Masks API tokens, database URIs, Authorization headers using deterministic SHA-256
digests, and detects verifiable canary leakage.
"""

import hashlib
import re
from typing import Any
import uuid

CANARY_PATTERN = re.compile(r"TL-CANARY-[0-9a-fA-F\-]{36}")
DB_URI_PATTERN = re.compile(
    r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s]+"
)
AUTH_HEADER_PATTERN = re.compile(
    r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9_\-\.=]+"
)
BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bBearer\s+([A-Za-z0-9_\-\.=]{20,})")
OPENAI_KEY_PATTERN = re.compile(r"\bsk-[a-zA-Z0-9_\-]{15,}\b")
GENERIC_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{10,})['\"]?"
)


def generate_canary() -> str:
    """Generate a verifiable unique canary token.

    Returns:
        A unique token formatted as 'TL-CANARY-<UUID>'.
    """
    return f"TL-CANARY-{uuid.uuid4()}"


def detect_canary_leak(text: str, canary: str | list[str]) -> bool:
    """Detect whether any canary token is present in the provided text.

    Args:
        text: Text string to inspect.
        canary: Single canary token string or list of canary tokens.

    Returns:
        True if any canary token is detected in unmasked form, False otherwise.
    """
    if isinstance(canary, str):
        return canary in text
    return any(c in text for c in canary)


def _hash_digest(val: str, prefix_len: int = 8) -> str:
    """Generate SHA-256 digest prefix for a secret."""
    return hashlib.sha256(val.encode("utf-8")).hexdigest()[:prefix_len]


class TelemetrySanitizer:
    """Sanitizes sensitive information from logs, traces, and metrics payloads."""

    def sanitize_text(self, text: str) -> str:
        """Mask credentials, tokens, DB connection strings, and canaries in text.

        Args:
            text: Raw telemetry text.

        Returns:
            Sanitized text with deterministic redactions.
        """
        if not text:
            return text

        # 1. Mask canaries
        def replace_canary(m: re.Match[str]) -> str:
            token = m.group(0)
            return f"[REDACTED_CANARY:{_hash_digest(token)}]"

        text = CANARY_PATTERN.sub(replace_canary, text)

        # 2. Mask Authorization headers
        def replace_auth(m: re.Match[str]) -> str:
            val = m.group(0)
            return f"[REDACTED_AUTH:{_hash_digest(val)}]"

        text = AUTH_HEADER_PATTERN.sub(replace_auth, text)

        # 3. Mask standalone Bearer tokens
        def replace_bearer(m: re.Match[str]) -> str:
            val = m.group(1)
            return f"Bearer [REDACTED_AUTH:{_hash_digest(val)}]"

        text = BEARER_TOKEN_PATTERN.sub(replace_bearer, text)

        # 4. Mask OpenAI style keys (sk-...)
        def replace_openai(m: re.Match[str]) -> str:
            val = m.group(0)
            return f"[REDACTED_SECRET:{_hash_digest(val)}]"

        text = OPENAI_KEY_PATTERN.sub(replace_openai, text)

        # 5. Mask Database URIs
        def replace_db_uri(m: re.Match[str]) -> str:
            val = m.group(0)
            return f"[REDACTED_URI:{_hash_digest(val)}]"

        text = DB_URI_PATTERN.sub(replace_db_uri, text)

        # 6. Mask generic api_key / secrets
        def replace_generic(m: re.Match[str]) -> str:
            key_name = m.group(1)
            val = m.group(2)
            return f"{key_name}=[REDACTED_SECRET:{_hash_digest(val)}]"

        text = GENERIC_SECRET_PATTERN.sub(replace_generic, text)

        return text

    def sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively sanitize keys and values in a dictionary.

        Args:
            data: Arbitrary dictionary.

        Returns:
            New dictionary with sanitized string values.
        """
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            cleaned_key = self.sanitize_text(str(k)) if isinstance(k, str) else k
            cleaned[cleaned_key] = self._sanitize_any(v)
        return cleaned

    def _sanitize_any(self, val: Any) -> Any:
        """Sanitize any nested structure."""
        if isinstance(val, str):
            return self.sanitize_text(val)
        if isinstance(val, dict):
            return self.sanitize_dict(val)
        if isinstance(val, list):
            return [self._sanitize_any(item) for item in val]
        return val
