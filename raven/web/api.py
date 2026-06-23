"""FastAPI backend for the RAVEN demo UI (M4).

Thin wrapper over services.py. The /api/benchmark route is the only LIVE LLM path; it
constructs a real AnthropicLLM (responses are disk-cached, so a warmed cache makes the
stage run instant). Run:  uvicorn raven.web.api:app --port 8000
"""

from __future__ import annotations

import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..llm import DEFAULT_MODEL, AnthropicLLM
from . import services

# /api/benchmark makes live (billable) API calls. A small server-side cooldown stops a
# refresh/mash loop from burning quota; the disk cache makes warmed calls free anyway.
_BENCH_COOLDOWN_S = 2.0
_last_benchmark = 0.0
_AB_COOLDOWN_S = 2.0
_last_ab = 0.0

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


@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...)):
    """M5: upload a PDF/doc -> it becomes agent memory; passports recomputed."""
    cap = 5_000_000
    buf = bytearray()
    while True:  # read in bounded chunks; reject BEFORE buffering the whole body
        chunk = await file.read(65536)
        if not chunk:
            break
        buf += chunk
        if len(buf) > cap:
            raise HTTPException(status_code=413, detail="File too large (5 MB max).")
    try:
        return services.ingest_document(bytes(buf), file.filename or "upload")
    except RuntimeError as exc:  # markitdown missing / unsupported format
        raise HTTPException(status_code=400, detail=str(exc))


class ABReq(BaseModel):
    prompt: str = Field(max_length=2000)
    memory: str = Field(default="", max_length=50_000)


@app.post("/api/ab")
def ab(req: ABReq):
    """LIVE A/B: answer the same prompt with full memory vs RAVEN passport; 2 billed calls."""
    global _last_ab
    now = time.monotonic()
    if now - _last_ab < _AB_COOLDOWN_S:
        raise HTTPException(status_code=429, detail="Rate-limited: A/B makes 2 live API calls; wait a moment.")
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Enter a prompt to send to both bots.")
    llm = AnthropicLLM(model=DEFAULT_MODEL)
    try:
        result = services.run_ab(llm, req.prompt, req.memory or None)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    _last_ab = time.monotonic()  # throttle only AFTER a successful billable call
    return result


@app.post("/api/benchmark")
def benchmark():
    """LIVE: runs the decision-preservation benchmark against the real API (cooldown'd)."""
    global _last_benchmark
    now = time.monotonic()
    if now - _last_benchmark < _BENCH_COOLDOWN_S:
        raise HTTPException(status_code=429, detail="Rate-limited: the benchmark makes live API calls; wait a moment.")
    llm = AnthropicLLM(model=DEFAULT_MODEL)
    try:
        result = services.run_benchmark(llm)
    except RuntimeError as exc:  # AnthropicLLM raises RuntimeError (key/HTTP/connection) -> clean 502
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    _last_benchmark = time.monotonic()  # throttle only AFTER a successful billable call
    return result
    # NOTE: any OTHER exception is a real backend bug -> let it 500 (visible, not disguised)
