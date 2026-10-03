"""GET /v1/view/{preset}. STUB (wp2): presets derived from golden surfaces, no model call."""

from __future__ import annotations

from collections.abc import Callable

from cac_serve.infra.metrics import metrics
from cac_serve.services.golden import load_golden

_BOOKING_TEXT = (
    "Request a table at The Kenmore. This is a request, not a confirmed reservation;"
    " the restaurant will confirm."
)
_CATERING_TEXT = "The Kenmore catering: Let us cater your next event! Request a catering quote."


def _as_preset(surface: dict, preset: str) -> dict:
    surface["surface_id"] = f"s_preset_{preset}"
    surface["kind"] = "preset"
    surface["meta"]["cache"] = "preset"
    return surface


def _menu() -> dict:
    return load_golden("preset_menu")


def _form(golden: str, preset: str, text: str) -> dict:
    surface = _as_preset(load_golden(golden), preset)
    view = surface["views"][0]
    view["data"]["prefill"] = {}
    view["text"] = text
    return surface


def _booking() -> dict:
    return _form("booking_form", "booking", _BOOKING_TEXT)


def _catering() -> dict:
    return _form("catering_form_40", "catering", _CATERING_TEXT)


def _hours() -> dict:
    return _as_preset(load_golden("hours_saturday"), "hours")


_PRESETS: dict[str, Callable[[], dict]] = {
    "menu": _menu,
    "booking": _booking,
    "catering": _catering,
    "hours": _hours,
}


def get_preset(preset: str, src: str | None = None) -> dict | None:
    """The Surface for a preset, or None when there is no such preset.

    `src == "cta"` means the visitor arrived by a goal button (OWNERSHIP seam 3).
    """
    build = _PRESETS.get(preset)
    if build is None:
        return None
    if src == "cta":
        metrics.incr_cta_clicked()
    return build()
