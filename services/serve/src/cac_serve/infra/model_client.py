"""The one constrained completion per uncached intent (SCHEMA 8.1).

Reached only through LLM_BASE_URL, which start-up has already checked is local. There is no
cloud client in this code base.
"""

from __future__ import annotations

import threading

import httpx
from cac_common.settings import get_settings

from cac_serve.infra.metrics import metrics

MODEL_TIMEOUT_S = 6.0
MAX_TOKENS = 96

_lock = threading.Lock()
_inflight = 0
_client = httpx.Client(timeout=MODEL_TIMEOUT_S)


class ModelBusy(Exception):
    """More than MODEL_MAX_INFLIGHT calls are already in flight."""


class ModelError(Exception):
    """Timeout, transport error or a malformed completion."""


def _acquire(limit: int) -> None:
    global _inflight
    with _lock:
        if _inflight >= limit:
            raise ModelBusy()
        _inflight += 1
    metrics.model_call_started()


def _release() -> None:
    global _inflight
    with _lock:
        _inflight -= 1
    metrics.model_call_finished()


def request_body(model: str, messages: list[dict], schema: dict) -> dict:
    return {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "stop": ["\n\n"],  # a finished JSON object is never followed by a blank line
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "selection", "schema": schema, "strict": True},
        },
        "reasoning_effort": "none",  # Ollama (the box)
        "chat_template_kwargs": {"enable_thinking": False},  # vLLM
    }


def complete(messages: list[dict], schema: dict) -> str:
    """Return the completion text. Raises ModelBusy or ModelError; never retries."""
    settings = get_settings()
    _acquire(settings.model_max_inflight)
    try:
        response = _client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            json=request_body(settings.llm_model, messages, schema),
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise ModelError(type(exc).__name__) from exc
    finally:
        _release()
    if not isinstance(content, str):
        raise ModelError("empty completion")
    return content


def warm_up(timeout_s: float = 120.0) -> bool:
    """Load the model into memory so the first visitor does not pay the cold start (a cold
    load can exceed the 6 s request timeout). Not counted in the metrics. Never raises."""
    settings = get_settings()
    body = {"model": settings.llm_model, "max_tokens": 1, "temperature": 0,
            "messages": [{"role": "user", "content": "ok"}], "reasoning_effort": "none"}
    try:
        url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        return httpx.post(url, json=body, timeout=timeout_s).status_code == 200
    except httpx.HTTPError:
        return False
