"""
API token pricing for supported LLM providers and models.

Rates are per 1 million tokens (USD).  Update these when providers
change their pricing pages:
  - OpenAI:    https://openai.com/api/pricing/
  - Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
  - Google:    https://ai.google.dev/gemini-api/docs/pricing
"""

from __future__ import annotations

# ── Pricing table ────────────────────────────────────────────────────
# Keys: (provider, model) → {"input": $, "cached": $, "output": $}
# All rates are per 1 million tokens (USD).
# Provider names match config.settings.LLM_PROVIDER (lowercase).

MODEL_PRICING: dict[tuple[str, str], dict[str, float]] = {
    # ── OpenAI ───────────────────────────────────────────────────────
    ("openai", "gpt-4o-mini"): {"input": 0.15, "cached": 0.075, "output": 0.60},
    ("openai", "gpt-4o"): {"input": 2.50, "cached": 1.25, "output": 10.00},
    ("openai", "gpt-4.1-nano"): {"input": 0.10, "cached": 0.025, "output": 0.40},
    ("openai", "gpt-4.1-mini"): {"input": 0.40, "cached": 0.10, "output": 1.60},
    ("openai", "gpt-4.1"): {"input": 2.00, "cached": 0.50, "output": 8.00},
    ("openai", "gpt-5"): {"input": 1.25, "cached": 0.125, "output": 10.00},
    ("openai", "gpt-5.2"): {"input": 1.75, "cached": 0.175, "output": 14.00},
    # ── Anthropic (cache hits = 0.1× base input) ────────────────────
    ("anthropic", "claude-haiku-4-5-20251001"): {
        "input": 1.00,
        "cached": 0.10,
        "output": 5.00,
    },
    ("anthropic", "claude-sonnet-4-5-20250929"): {
        "input": 3.00,
        "cached": 0.30,
        "output": 15.00,
    },
    ("anthropic", "claude-opus-4-6"): {
        "input": 5.00,
        "cached": 0.50,
        "output": 25.00,
    },
    # ── Google Gemini ────────────────────────────────────────────────
    ("google", "gemini-2.5-flash-lite"): {
        "input": 0.10,
        "cached": 0.025,
        "output": 0.40,
    },
    ("google", "gemini-2.5-flash"): {
        "input": 0.30,
        "cached": 0.03,
        "output": 2.50,
    },
    ("google", "gemini-2.5-pro"): {
        "input": 1.25,
        "cached": 0.125,
        "output": 10.00,
    },
    ("google", "gemini-3-flash-preview"): {
        "input": 0.50,
        "cached": 0.05,
        "output": 3.00,
    },
    ("google", "gemini-3-pro-preview"): {
        "input": 2.00,
        "cached": 0.20,
        "output": 12.00,
    },
}


def get_token_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    """Calculate the total cost in USD for the given token counts.

    *cached_tokens* are subtracted from *input_tokens* and billed at
    the cheaper cached rate.  Returns 0.0 if the provider/model
    combination is not in the pricing table (e.g. local Ollama models).
    """
    rates = MODEL_PRICING.get((provider.lower(), model))
    if rates is None:
        return 0.0
    non_cached = max(input_tokens - cached_tokens, 0)
    input_cost = (non_cached / 1_000_000) * rates["input"]
    cached_cost = (cached_tokens / 1_000_000) * rates["cached"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    return input_cost + cached_cost + output_cost
