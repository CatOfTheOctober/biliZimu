"""I/O helpers for episode package files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EpisodePackage


def load_package(path: str | Path) -> EpisodePackage:
    file_path = Path(path)
    data: dict[str, Any] = json.loads(file_path.read_text(encoding="utf-8"))
    return EpisodePackage.from_dict(data)


def dump_json(path: str | Path, payload: Any) -> None:
    file_path = Path(path)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
