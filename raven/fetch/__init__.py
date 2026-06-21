"""Fetch.ai integration layer (uAgents / Agentverse / ASI:One).

This subpackage is the ONLY place that imports `uagents`. It is intentionally kept
out of the import path of the core engine and the test suite, so `pytest` stays
fully offline and has no dependency on `uagents`/`redis`/network.
"""
