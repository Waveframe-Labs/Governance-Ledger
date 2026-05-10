"""Path formatting helpers for portable governance artifacts."""

from __future__ import annotations

from pathlib import Path


def artifact_path(path: str | Path) -> str:
    """Return a stable POSIX-style path string for JSON artifacts."""
    return Path(path).as_posix().replace("\\", "/")
