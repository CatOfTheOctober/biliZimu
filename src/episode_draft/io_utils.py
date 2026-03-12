"""I/O helpers for episode draft generation."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import EpisodeDraft


def resolve_bundle_paths(bundle_dir: str | Path) -> dict[str, Path]:
    root = Path(bundle_dir).resolve()
    return {
        "bundle_dir": root,
        "transcript": root / "derived" / "TranscriptBundle.json",
        "video_metadata": root / "raw" / "video_metadata.json",
        "manifest": root / "manifest" / "AssetManifest.json",
        "review_dir": root / "review",
        "draft": root / "review" / "EpisodeDraft.json",
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    paths = resolve_bundle_paths(bundle_dir)
    transcript_path = paths["transcript"]
    if not transcript_path.exists():
        raise FileNotFoundError(f"TranscriptBundle not found: {transcript_path}")

    bundle = load_json(transcript_path)
    video_metadata = load_json(paths["video_metadata"]) if paths["video_metadata"].exists() else {}
    manifest = load_json(paths["manifest"]) if paths["manifest"].exists() else {}
    return {
        "paths": paths,
        "transcript_bundle": bundle,
        "video_metadata": video_metadata,
        "manifest": manifest,
    }


def write_draft(draft: EpisodeDraft, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(draft), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
