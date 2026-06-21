"""LLM access for M2.

- AnthropicLLM: uses the `anthropic` SDK if importable, else a stdlib `urllib`
  POST to the Messages API. temperature=0. Disk-cached so re-runs are free and
  repeatable. Reports real input/output token usage.
- FakeLLM: deterministic, offline, injectable into agents for tests (NO network).

Nothing here is imported at module load that requires the SDK or network; tests
use FakeLLM exclusively.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Callable, Optional

from .tokens import count_tokens

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".llmcache")


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int


class BaseLLM:
    def complete(self, system: str, user: str, max_tokens: int = 512) -> LLMResult:
        raise NotImplementedError


class FakeLLM(BaseLLM):
    """Deterministic offline LLM. `responder(system, user) -> str` supplies the
    reply; token counts are derived with the same offline counter used elsewhere."""

    def __init__(self, responder: Callable[[str, str], str]):
        self._responder = responder
        self.calls = 0

    def complete(self, system: str, user: str, max_tokens: int = 512) -> LLMResult:
        self.calls += 1
        text = self._responder(system, user)
        return LLMResult(
            text=text,
            input_tokens=count_tokens(system + "\n" + user, backend="fallback"),
            output_tokens=count_tokens(text, backend="fallback"),
        )


class AnthropicLLM(BaseLLM):
    def __init__(self, model: str = DEFAULT_MODEL, cache: bool = True, temperature: float = 0.0):
        self.model = model
        self.cache = cache
        self.temperature = temperature

    def _cache_path(self, key: str) -> str:
        return os.path.join(_CACHE_DIR, key + ".json")

    def _key(self, system: str, user: str, max_tokens: int) -> str:
        blob = json.dumps(
            {"m": self.model, "t": self.temperature, "mt": max_tokens, "s": system, "u": user},
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]

    def complete(self, system: str, user: str, max_tokens: int = 512) -> LLMResult:
        key = self._key(system, user, max_tokens)
        if self.cache:
            try:
                with open(self._cache_path(key), encoding="utf-8") as fh:
                    d = json.load(fh)
                return LLMResult(d["text"], d["input_tokens"], d["output_tokens"])
            except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError):
                pass  # missing or corrupt cache entry -> just recompute
        result = self._call_api(system, user, max_tokens)
        if self.cache:
            self._write_cache(key, result)
        return result

    def _write_cache(self, key: str, result: LLMResult) -> None:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        path = self._cache_path(key)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(result.__dict__, fh)
        os.replace(tmp, path)  # atomic on Windows + POSIX; no half-written cache files

    def _call_api(self, system: str, user: str, max_tokens: int) -> LLMResult:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": self.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        # Prefer the SDK; fall back to stdlib urllib so there is no hard dependency.
        try:
            import anthropic  # type: ignore

            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(**body)
            text = "".join(getattr(b, "text", "") for b in resp.content)
            return LLMResult(text, resp.usage.input_tokens, resp.usage.output_tokens)
        except ImportError:
            return self._call_urllib(api_key, body)

    @staticmethod
    def _call_urllib(api_key: str, body: dict) -> LLMResult:
        import urllib.error
        import urllib.request

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:  # 4xx/5xx -> surface the API's error body
            detail = ""
            try:
                detail = e.read().decode("utf-8")
            except Exception:
                pass
            raise RuntimeError(f"Anthropic API HTTP {e.code}: {detail[:500]}") from e
        except urllib.error.URLError as e:  # connection/timeout
            raise RuntimeError(f"Anthropic API connection error: {e.reason}") from e
        if payload.get("type") == "error" or "content" not in payload or "usage" not in payload:
            raise RuntimeError(f"Anthropic API unexpected response: {str(payload)[:500]}")
        text = "".join(part.get("text", "") for part in payload["content"])
        usage = payload["usage"]
        return LLMResult(text, usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def extract_json(text: str) -> Optional[dict]:
    """Parse the first JSON object in a model reply. Uses raw_decode, which is
    string/escape-aware (so a brace inside a string value doesn't break it) and
    ignores trailing prose."""
    if not text:
        return None
    decoder = json.JSONDecoder()
    i = text.find("{")
    while i != -1:
        try:
            obj, _ = decoder.raw_decode(text, i)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        i = text.find("{", i + 1)
    return None
