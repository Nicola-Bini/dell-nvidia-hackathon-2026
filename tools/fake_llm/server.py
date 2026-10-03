# /// script
# requires-python = ">=3.12"
# dependencies = ["fastapi>=0.115", "uvicorn>=0.30", "jsonschema>=4.23"]
# ///
"""OpenAI-compatible stand-in for the local model, for laptops (OWNERSHIP seam 6).

Run: `uv run tools/fake_llm/server.py --port 8000`. No model, no network: selections come
from the keyword rules in rules.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Body, FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import select  # noqa: E402

MODEL_ID = "fake-llm"
VISITOR_MARK = "\nVisitor: "

app = FastAPI(title="CAC fake model")
_lock = threading.Lock()
_stats = {"calls": 0}


def _content(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)


def parse_user_message(content: str) -> tuple[list[dict[str, str]], str]:
    """Candidates from the `<data>` block and the visitor's text after the last marker."""
    head, mark, visitor = content.rpartition(VISITOR_MARK)
    if not mark:
        head, visitor = "", content.removeprefix(VISITOR_MARK.lstrip("\n"))
    block = head.split("<data>\n", 1)[-1].split("\n</data>", 1)[0] if "<data>" in head else ""
    candidates = []
    for line in block.split("\n"):
        fields = [part.strip() for part in line.split(" | ", 3)]
        if len(fields) >= 3 and fields[0]:
            fields += [""] * (4 - len(fields))
            candidates.append(dict(zip(("id", "label", "name", "facts"), fields, strict=True)))
    return candidates, visitor.strip()


def _schema_of(body: dict[str, Any]) -> dict:
    response_format = body.get("response_format") or {}
    return (response_format.get("json_schema") or {}).get("schema") or {}


@app.get("/v1/models")
def models() -> dict:
    return {"object": "list", "data": [{"id": MODEL_ID, "object": "model"}]}


@app.post("/v1/chat/completions")
def chat_completions(body: dict[str, Any] = Body(...)) -> dict:  # noqa: B008
    with _lock:
        _stats["calls"] += 1
        call_number = _stats["calls"]
    messages = body.get("messages") or [{}]
    candidates, text = parse_user_message(_content(messages[-1]))
    selection = select(_schema_of(body), candidates, text)
    content = json.dumps(selection, separators=(",", ":"))
    return {
        "id": f"chatcmpl-fake-{call_number}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model") or MODEL_ID,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.get("/stats")
def stats() -> dict:
    with _lock:
        return {"calls": _stats["calls"]}


@app.post("/reset")
def reset() -> dict:
    with _lock:
        _stats["calls"] = 0
    return {"calls": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAI-compatible fake model for CAC")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
