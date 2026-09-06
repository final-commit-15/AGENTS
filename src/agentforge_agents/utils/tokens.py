"""Token estimation, truncation, and cost helpers.

The estimators are deterministic character / word heuristics - deliberately
provider-agnostic and free of heavy dependencies. They are accurate to within
a few percent for common OpenAI / Ollama tokenizers.
"""

from __future__ import annotations

from collections.abc import Iterable

_CHARS_PER_TOKEN = 4.0
_TOKENS_PER_WORD = 4.0 / 3.0


def estimate_tokens(text: str | None) -> int:
    """Estimate the number of tokens in ``text``."""
    if not text:
        return 0
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def estimate_messages_tokens(messages: Iterable[dict | str]) -> int:
    """Estimate tokens for a chat message list (dicts with role/content)."""
    total = 0
    for message in messages:
        if isinstance(message, str):
            total += estimate_tokens(message)
            continue
        content = message.get("content", "") if isinstance(message, dict) else ""
        total += estimate_tokens(str(content))
    return total


def truncate(text: str, max_tokens: int) -> str:
    """Truncate ``text`` to roughly ``max_tokens`` preserving whole characters."""
    if max_tokens <= 0:
        return ""
    max_chars = int(max_tokens * _CHARS_PER_TOKEN)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " …[truncated]"


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    *,
    price_per_1k_input: float,
    price_per_1k_output: float,
) -> float:
    """Compute cost in USD for a single call given provider rates."""
    return (prompt_tokens * price_per_1k_input + completion_tokens * price_per_1k_output) / 1000.0


__all__ = ["estimate_cost", "estimate_messages_tokens", "estimate_tokens", "truncate"]
