"""Pytest configuration for ensuring correct import paths and debugging.

This file ensures the `src/` package layout is prioritized on sys.path so that
`memory` resolves to `src/memory` during test collection and execution.
It also prints basic diagnostics at session start to aid debugging when needed.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_first_on_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    # Insert src at the very front and remove duplicates later
    if src.exists():
        sys.path.insert(0, str(src))

    # Optional: ensure any \"app\" path comes after src to avoid shadowing `memory`
    app_dir = repo_root / "app"
    if str(app_dir) in sys.path:
        # Move existing app path to the end to avoid taking precedence over src
        try:
            sys.path.remove(str(app_dir))
        except ValueError:
            pass
        sys.path.append(str(app_dir))

    # De-duplicate sys.path while preserving order
    seen = set()
    unique = []
    for p in sys.path:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    sys.path[:] = unique


def pytest_sessionstart(session):  # noqa: D401 (pytest hook)
    """Called after the ``Session`` object has been created and before performing collection."""
    _ensure_src_first_on_syspath()

    # Lightweight diagnostics to help identify shadowing issues during CI runs
    try:
        import importlib

        print("\n[pytest] sys.path (head):", sys.path[:5])
        memory_mod = importlib.import_module("memory")
        print("[pytest] memory module file:", getattr(memory_mod, "__file__", None))
    except Exception as exc:  # pragma: no cover - best-effort diagnostics
        print(f"[pytest] diagnostics failed: {exc}")
