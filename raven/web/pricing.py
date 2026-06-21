"""Rough $ estimate for the token meter.

NOT authoritative -- these are APPROXIMATE per-million-token rates; adjust to your
model's real pricing. Tokens remain the primary, honest metric throughout RAVEN.
"""

PRICE_PER_MTOK_IN = 1.0   # approximate $/Mtok input; adjust
PRICE_PER_MTOK_OUT = 5.0  # approximate $/Mtok output; adjust


def est_cost_usd(total_tokens: int, in_frac: float = 0.85) -> float:
    """Estimate $ from a combined token count by assuming an input/output split.
    Clearly an approximation (we only track combined tokens in the UI path)."""
    inp = total_tokens * in_frac
    out = total_tokens * (1.0 - in_frac)
    return round(inp / 1_000_000 * PRICE_PER_MTOK_IN + out / 1_000_000 * PRICE_PER_MTOK_OUT, 6)
