#!/usr/bin/env python3
"""Compatibility import for the completed detached P0 native attribution tests.

P0 mapper is now implemented once, at the installed backend path. The original
P0 fixture still exercises build_map/lookup against actual generator stages.
The production P2d emitter is nonactivating and has its own bounded CLI.
"""
from __future__ import annotations

from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[2] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from auto_detect_origin_map import AttributionError, build_map, lookup
