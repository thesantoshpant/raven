"""Warm the .llmcache before a demo so the live benchmark is instant.

Runs the decision benchmark once against the real API; every call is then disk-cached,
so the on-stage "Run benchmark" returns immediately. Run from the repo root:

    python bench/warm_cache.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raven.llm import DEFAULT_MODEL, AnthropicLLM  # noqa: E402
from raven.web import services  # noqa: E402


def main():
    print(f"Warming cache via {DEFAULT_MODEL} (live API calls; cached after the first run)...")
    out = services.run_benchmark(AnthropicLLM(model=DEFAULT_MODEL))
    print(f"per-agent budget: {out['per_agent_budget']} tok")
    for cond, d in out["conditions"].items():
        miss = f" missed={d['missed']}" if d["missed"] else ""
        print(f"  {cond:<8} {d['constraints']}/{d['total']}  {d['agent_tokens']} tok{miss}")
    print("Cache warm -> the UI 'Run benchmark' button is now instant + reliable.")


if __name__ == "__main__":
    main()
