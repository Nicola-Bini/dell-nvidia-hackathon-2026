"""Helpers for scripts/seed.py: registries, the graph builder and the database writes."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# cac_common is an editable install in tests/pyproject.toml. macOS can flag the venv's .pth
# file as hidden, and Python 3.12 then skips it, so the package is also added by path.
_COMMON = str(ROOT / "packages" / "cac_common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
