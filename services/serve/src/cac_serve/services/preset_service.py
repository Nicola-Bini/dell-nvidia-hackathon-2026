"""GET /v1/view/{preset}: fixed surfaces bound from the published graph, no model call."""

from __future__ import annotations

from cac_common.settings import get_settings

from cac_serve.domain import binder
from cac_serve.infra import db
from cac_serve.infra.graph_repo import load_graph
from cac_serve.infra.metrics import metrics
from cac_serve.services.pipeline import GraphNotPublished, business_today


def get_preset(preset: str, src: str | None = None) -> dict | None:
    """The Surface for a preset, or None when there is no such preset.

    `src == "cta"` means the visitor arrived by a goal button (OWNERSHIP seam 3).
    """
    settings = get_settings()
    with db.snapshot() as conn:
        graph = load_graph(conn, settings.business_id)
    if graph.version == 0:
        raise GraphNotPublished()
    surface = binder.preset_surface(graph, preset, business_today(settings))
    if surface is None:
        return None
    if src == "cta":
        metrics.incr_cta_clicked()
    if binder.steer_shown(surface):
        metrics.incr_cta_shown()
    return surface
