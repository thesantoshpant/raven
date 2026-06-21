"""FastAPI backend for the RAVEN demo UI (M4).

Thin wrapper over services.py. The /api/benchmark route is the only LIVE LLM path; it
constructs a real AnthropicLLM (responses are disk-cached, so a warmed cache makes the
stage run instant). Run:  uvicorn raven.web.api:app --port 8000
"""

from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..llm import DEFAULT_MODEL, AnthropicLLM
from . import services

# /api/benchmark makes live (billable) API calls. A small server-side cooldown stops a
# refresh/mash loop from burning quota; the disk cache makes warmed calls free anyway.
_BENCH_COOLDOWN_S = 2.0
_last_benchmark = 0.0

app = FastAPI(title="RAVEN demo API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",  # Next falls back to 3001 if 3000 is busy
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "model": DEFAULT_MODEL}


@app.get("/api/scenario")
def scenario():
    return services.get_scenario()


@app.get("/api/passports")
def passports():
    return services.role_passports()


@app.get("/api/relay")
def relay():
    return services.relay_demo()


class CompressReq(BaseModel):
    role: str = "budget"
    task: str = "plan a friday dinner"
    memory: str = Field(max_length=50_000)


@app.post("/api/compress")
def compress(req: CompressReq):
    return services.compress(req.role, req.task, req.memory)


@app.post("/api/benchmark")
def benchmark():
    """LIVE: runs the decision-preservation benchmark against the real API (cooldown'd)."""
    global _last_benchmark
    now = time.monotonic()
    if now - _last_benchmark < _BENCH_COOLDOWN_S:
        raise HTTPException(status_code=429, detail="Rate-limited: the benchmark makes live API calls; wait a moment.")
    _last_benchmark = now
    llm = AnthropicLLM(model=DEFAULT_MODEL)
    try:
        return services.run_benchmark(llm)
    except RuntimeError as exc:  # AnthropicLLM raises RuntimeError (key/HTTP/connection) -> clean 502
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    # NOTE: any OTHER exception is a real backend bug -> let it 500 (visible, not disguised)
