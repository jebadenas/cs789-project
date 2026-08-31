"""Single choke-point for every model call.

Swap ``BACKEND`` (or pass ``backend=``) to move the whole pipeline between a
local Ollama model, the cluster's vLLM server, or the Gemini API without
touching any pipeline code. Only Ollama is wired up now.
"""

from __future__ import annotations

import json
import os
import urllib.request

# Default local trial model. Override with LLM_MODEL / LLM_BACKEND env vars.
BACKEND = os.environ.get("LLM_BACKEND", "ollama")
MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
# OpenAI-compatible endpoint — vLLM on the cluster now; Gemini's compat URL later.
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "EMPTY")  # vLLM ignores the key
# Big blobs (up to ~67k tokens) can prefill for many minutes on a small local
# model — keep this generous so slow teams don't spuriously time out.
TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "1800"))


def call_model(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.2,
    num_ctx: int = 32768,
    max_tokens: int = 1500,
    response_format: dict | None = None,
    backend: str | None = None,
    model: str | None = None,
) -> str:
    """Return the model's text response for ``prompt``.

    Backend is a one-line swap (``LLM_BACKEND`` env or ``backend=``):
    ``ollama`` (local trial) or ``openai`` (vLLM on the cluster / Gemini compat).
    ``num_ctx`` matters only for Ollama — it must exceed the largest team blob
    (~41k tokens) or the journals are silently truncated; vLLM/Gemini fix context
    server-side. Keep ``temperature`` low for extraction; the consistency check
    (§7) varies member order, not sampling noise.
    """
    backend = backend or BACKEND
    if backend == "ollama":
        return _ollama(prompt, system, temperature, num_ctx, model or MODEL)
    if backend == "openai":
        return _openai(prompt, system, temperature, max_tokens, response_format, model or MODEL)
    raise NotImplementedError(f"backend {backend!r} not wired up yet")


def _openai(prompt, system, temperature, max_tokens, response_format, model) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    req = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = json.load(resp)
    return body["choices"][0]["message"]["content"]


def _ollama(prompt, system, temperature, num_ctx, model) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = json.load(resp)
    return body["message"]["content"]
