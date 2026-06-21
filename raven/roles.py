"""Recipient (role) definitions: what each downstream agent actually needs.

This is the heart of "recipient-aware" compression: a fact is only included in a
passport if it matters to THAT agent's job. `CRITICAL_TYPES` are force-kept by the
exact-span guard (the constraints whose loss flips the decision).
"""

ROLES = {
    "restaurant": {
        "types": {"dietary", "preference", "budget_limit", "location"},
        "keywords": [
            "restaurant", "food", "dinner", "cuisine", "vegetarian", "vegan",
            "loud", "quiet", "noise", "budget", "price", "near", "location", "menu",
        ],
    },
    "calendar": {
        "types": {"availability"},
        "keywords": [
            "calendar", "free", "busy", "time", "schedule", "friday", "evening",
            "lab", "class", "until", "after", "before", "pm", "am",
        ],
    },
    "budget": {  # the budget / payment agent
        "types": {"budget_limit", "permission"},
        "keywords": [
            "budget", "price", "cost", "spend", "dollar", "confirm", "approve",
            "payment", "pay", "before", "permission",
        ],
    },
    "writer": {  # the final summarizer: needs the decisions + constraints, not receipts
        "types": {"dietary", "budget_limit", "availability", "permission", "preference", "location"},
        "keywords": [
            "summary", "plan", "recommend", "prefer", "like", "vegetarian", "budget",
            "time", "confirm", "venue", "quiet",
        ],
    },
}

# Stable order = the agent pipeline used by the benchmark (n_agents = len).
ROLE_ORDER = ["restaurant", "calendar", "budget", "writer"]

# Types the exact-span guard must always include for a role if present in the store.
CRITICAL_TYPES = {
    "restaurant": {"dietary"},
    "calendar": {"availability"},
    "budget": {"budget_limit", "permission"},
    "writer": set(),
}
