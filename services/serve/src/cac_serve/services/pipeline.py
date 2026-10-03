"""The intent pipeline (SCHEMA 8.5): slots, cache, retrieve, one model call, bind, log.

Graph reads happen in one REPEATABLE READ, READ ONLY transaction that loads the published
graph into memory; the model call and binding then work on that snapshot, so one request
sees one graph version and no transaction is held open while the model runs.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

import jsonschema
from cac_common.settings import Settings, get_settings

from cac_serve.domain import binder, shortcuts
from cac_serve.domain.graph import Graph
from cac_serve.domain.normalize import normalized_hash
from cac_serve.domain.prompt import build_messages
from cac_serve.domain.retrieve import retrieve
from cac_serve.domain.schema_builder import build_schema
from cac_serve.domain.slots import extract_slots, slots_key
from cac_serve.infra import cache_repo, db, log_repo, model_client
from cac_serve.infra.graph_repo import load_graph
from cac_serve.infra.metrics import metrics

MODEL_LABEL = "local"
MAX_TOPIC_CHARS = 60


class GraphNotPublished(Exception):
    """kg_public is empty: nothing has been published for this business yet."""


@dataclass
class Outcome:
    """What one intent produced. `selection` and `schema` are kept for tests and the log."""

    surface: dict
    kind: str
    cache: str
    selection: dict | None = None
    schema: dict | None = None
    candidates: list[str] = field(default_factory=list)
    model_calls: int = 0


def business_today(settings: Settings) -> date:
    """Today in the business timezone. CAC_TODAY pins it for tests and rehearsals."""
    pinned = os.environ.get("CAC_TODAY")
    if pinned:
        return date.fromisoformat(pinned)
    return datetime.now(ZoneInfo(settings.tz)).date()


def _check(graph: Graph, candidates: list[str], schema: dict, raw: str) -> tuple[dict, list[str]]:
    """Parse and validate one completion: JSON, the request's schema, then binder rule 1."""
    try:
        selection = json.loads(raw)
        jsonschema.validate(selection, schema)
    except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
        message = getattr(exc, "message", None) or "the reply was not valid JSON"
        return {}, [message]
    if selection.get("kind") != "answer":
        return selection, []
    return binder.clean_selection(graph, candidates, selection)


def _select(graph: Graph, candidates: list[str], text: str) -> tuple[dict | None, dict, int]:
    """One constrained model call, retried once with the error. None means "busy"."""
    schema = build_schema(graph, candidates)
    messages = build_messages(graph, candidates, text)
    calls = 0
    for _attempt in range(2):
        try:
            calls += 1
            raw = model_client.complete(messages, schema)
        except (model_client.ModelBusy, model_client.ModelError):
            return None, schema, calls
        selection, errors = _check(graph, candidates, schema, raw)
        if not errors:
            return selection, schema, calls
        messages = [*messages, {"role": "assistant", "content": raw[:400]},
                    {"role": "user", "content": "Invalid: " + "; ".join(errors)[:300]
                     + ". Reply again with JSON that matches the schema."}]
    return None, schema, calls


def _shortcut(graph: Graph, text: str, today: date) -> Outcome | None:
    """A chip or nav label that opens a preset: no cache, no model (domain/shortcuts.py)."""
    preset = shortcuts.preset_for(graph, text)
    surface = binder.preset_surface(graph, preset, today) if preset else None
    return Outcome(surface, "preset", "preset") if surface is not None else None


def _finish(outcome: Outcome, graph: Graph, started: float) -> Outcome:
    latency = int((time.perf_counter() - started) * 1000)
    outcome.surface["meta"] = {"cache": outcome.cache, "latency_ms": latency,
                               "graph_version": graph.version, "model": MODEL_LABEL}
    return outcome


def answer(text: str, today: date, settings: Settings) -> tuple[Outcome, Graph, dict, float]:
    """Run the pipeline for one text. No logging and no metrics: see run_intent."""
    started = time.perf_counter()
    slots = extract_slots(text, today)
    with db.snapshot() as conn:
        graph = load_graph(conn, settings.business_id)
        if graph.version == 0:
            raise GraphNotPublished()
        shortcut = _shortcut(graph, text, today)
        if shortcut is not None:
            return _finish(shortcut, graph, started), graph, slots, started
        key = cache_repo.CacheKey(settings.business_id, graph.version,
                                  normalized_hash(text), slots_key(slots))
        cached = cache_repo.lookup(conn, key)
        candidates = [] if cached is not None else retrieve(conn, graph, text, slots)
    if cached is not None:
        surface = binder.bind(graph, cached, slots, today)
        outcome = Outcome(surface, surface["kind"], "exact", cached)
        with db.writer() as conn:
            cache_repo.record_hit(conn, key)
        return _finish(outcome, graph, started), graph, slots, started
    selection, schema, calls = _select(graph, candidates, text)
    if selection is None:
        outcome = Outcome(binder.busy_surface(graph, today), "error", "preset",
                          None, schema, candidates, calls)
        return _finish(outcome, graph, started), graph, slots, started
    with db.writer() as conn:
        cache_repo.store(conn, key, selection)
    surface = binder.bind(graph, selection, slots, today)
    outcome = Outcome(surface, surface["kind"], "miss", selection, schema, candidates, calls)
    return _finish(outcome, graph, started), graph, slots, started


def gap_topic(graph: Graph, outcome: Outcome) -> str | None:
    """The topic the owner is asked about. The model's phrase, or, when an answer bound to
    nothing (a diet with no dishes), the name of the node it pointed at."""
    if outcome.kind != "gap":
        return None
    selection = outcome.selection or {}
    if selection.get("topic"):
        return str(selection["topic"])[:MAX_TOPIC_CHARS]
    for view in selection.get("views") or []:
        for key in ("diet", "section", "allergen", "faq", "node"):
            node = graph.get(view.get(key) or "")
            if node is not None:
                return node.name[:MAX_TOPIC_CHARS]
    return "unknown"


def run_intent(text: str, session_id: str | None, channel: str) -> Outcome:
    """Answer one intent, then log it and count it. Raw text goes only to ops.intent_log."""
    settings = get_settings()
    outcome, graph, slots, _started = answer(text, business_today(settings), settings)
    entry = log_repo.LogEntry(
        business_id=settings.business_id, channel=channel, session_id=session_id, text=text,
        cache=outcome.cache, kind=outcome.kind,
        latency_ms=outcome.surface["meta"]["latency_ms"],
        graph_version=graph.version, slots=slots, selection=outcome.selection,
        gap_topic=gap_topic(graph, outcome),
        model=settings.llm_model if outcome.model_calls else None,
    )
    with db.writer() as conn:
        log_repo.insert(conn, entry)
    if outcome.cache != "preset":
        metrics.record_cache(outcome.cache == "exact")
    if binder.steer_shown(outcome.surface):
        metrics.incr_cta_shown()
    return outcome
