"""Shared utility helpers for the placement subpackage."""

from __future__ import annotations

import sys


def snap(v: float) -> float:
    """Snap a coordinate to the 0.5 mm grid."""
    return round(v * 2) / 2


def log(msg: str) -> None:
    """Emit a log line to stderr with ``[placement]`` prefix."""
    print(f"[placement] {msg}", file=sys.stderr)
