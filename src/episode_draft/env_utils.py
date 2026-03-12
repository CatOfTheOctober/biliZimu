"""Environment loading helpers for episode_draft."""

from __future__ import annotations

import os
from pathlib import Path


def load_project_env() -> Path | None:
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and _should_override_env(key):
            os.environ[key] = value

    return env_path


def _should_override_env(key: str) -> bool:
    if key.startswith("EPISODE_DRAFT_"):
        return True
    if key in {"MODELSCOPE_CACHE", "OLLAMA_MODELS"}:
        return True
    return key not in os.environ
