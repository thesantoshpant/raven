"""RELAY bench: agent -> agent handoff compression, honestly framed.

At each handoff the next agent needs (a) the upstream agent's LATEST message and (b)
the still-relevant back-context from earlier hops. We compare three strategies:

  full_transcript : forward the ENTIRE running transcript every hop (naive upper bound)
  last_message    : forward ONLY the upstream agent's latest output (cheap, but DROPS
                    earlier standing constraints -- e.g. "Maya is vegetarian")
  RAVEN RELAY     : forward the latest message verbatim + a recipient-aware compressed
                    passport of the back-context (cheap AND keeps the back-context criticals)

So RELAY's honest claim is NOT "93% smaller than everything" -- it is: far cheaper than
broadcasting the full transcript, modestly more than last-message-only, and (unlike
last-message) it preserves the back-context constraints that last-message silently drops.
Offline + deterministic (scripted agent outputs, no LLM/network). SINGLE
illustrative scenario; numbers are scale-driven (a passport has ~25-30 tok of fixed
structure, so RELAY only beats raw text once the handoff exceeds that).
Run from the repo root:  python bench/run_relay.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raven.ingest import load_corpus  # noqa: E402
from raven.baselines import serialize_corpus  # noqa: E402
from raven.relay import build_relay_passport  # noqa: E402
from raven.tokens import count_tokens  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TASK = "plan a friday dinner with maya"

RESTAURANT_OUT = (
    "After reviewing the candidate venues and the user's notes, I recommend Green Bowl, "
    "a vegetarian-friendly and quiet spot at roughly $28 per person. I ruled out the "
    "steakhouse because Maya is vegetarian, and I avoided the loud cantina. We still need "
    "to confirm the timing against the user's calendar and clear the spend with the budget agent."
)
BUDGET_OUT = (
    "I checked the recommendation against the user's finances. Green Bowl at about $28 is "
    "comfortably under the $40 dinner cap for this month. Per the user's standing rule I am "
    "NOT auto-paying; I have flagged the payment to await the user's confirmation before booking."
)

# A back-context constraint that originates EARLY (user memory) and that a summarizer
# still needs at the final hop -- used to show last-message passing silently drops it.
BACKCTX_PROBE = "vegetarian"


def main():
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    memory = serialize_corpus(corpus)

    # (to_role, prior_context_so_far, latest_upstream_message)
    hops = [
        ("restaurant", memory, ""),
        ("budget", memory, RESTAURANT_OUT),
        ("writer", memory + "\n" + RESTAURANT_OUT, BUDGET_OUT),
    ]

    header = f"{'hop':<14}{'full_transcript':>16}{'last_message':>14}{'RAVEN_relay':>13}{'vs_full':>9}"
    print(__doc__.strip().splitlines()[0] + "\n")
    print(header)
    print("-" * len(header))

    tot_full = tot_last = tot_relay = 0
    relay_keeps = last_keeps = 0
    for to_role, prior, msg in hops:
        full = count_tokens((prior + "\n" + msg).strip(), backend="fallback")
        last = count_tokens(msg, backend="fallback")
        # RELAY = recipient-aware compressed back-context + the latest message VERBATIM (message floor).
        prior_res = build_relay_passport(prior, TASK, to_role, backend="fallback")
        relay_text = prior_res.passport_text + (f"\n\nLATEST FROM UPSTREAM:\n{msg}" if msg.strip() else "")
        relay = count_tokens(relay_text, backend="fallback")

        tot_full += full
        tot_last += last
        tot_relay += relay
        # Does each strategy still carry the early back-context constraint at this hop?
        relay_keeps += int(BACKCTX_PROBE in relay_text.lower())
        last_keeps += int(BACKCTX_PROBE in msg.lower())

        vs_full = (1 - relay / full) * 100 if full else 0.0
        print(f"{'-> ' + to_role:<14}{full:>16}{last:>14}{relay:>13}{f'{vs_full:.0f}%':>9}")

    print("-" * len(header))
    print(f"{'TOTAL':<14}{tot_full:>16}{tot_last:>14}{tot_relay:>13}"
          f"{f'{(1 - tot_relay / tot_full) * 100:.0f}%':>9}")

    print(
        f"\nHandoff cost: full_transcript={tot_full} tok, last_message={tot_last} tok, "
        f"RAVEN_relay={tot_relay} tok.\n"
        f"RELAY costs more than last-message-only (it adds the compressed back-context) but "
        f"PRESERVES the early back-context constraint ('{BACKCTX_PROBE}') on {relay_keeps}/{len(hops)} "
        f"hops, vs last-message on only {last_keeps}/{len(hops)} -- last-message silently drops "
        f"standing constraints from earlier hops.\n"
        f"vs the naive full-transcript broadcast, RELAY is {(1 - tot_relay / tot_full) * 100:.0f}% smaller.\n"
        "NOTE: single illustrative scenario; scripted (no LLM). Savings are scale-driven -- a "
        "passport's ~25-30 tok of fixed structure means RELAY only wins once the handoff exceeds that."
    )


if __name__ == "__main__":
    main()
