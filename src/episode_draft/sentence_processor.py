"""Sentence normalization for EpisodeDraft generation."""

from __future__ import annotations

from typing import Any


NOISE_MARKERS = (
    "点赞",
    "关注",
    "投币",
    "收藏",
    "转发",
    "下期再见",
)

CONNECTIVE_PREFIXES = (
    "那么",
    "然后",
    "接下来",
    "再说",
    "另外",
    "此外",
    "还有",
    "先说",
    "下面",
)


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\u3000", " ").split()).strip()


def is_noise_text(text: str) -> bool:
    stripped = normalize_text(text)
    if not stripped:
        return True
    return any(marker in stripped for marker in NOISE_MARKERS)


def should_merge_short_segment(current: dict[str, Any], next_segment: dict[str, Any] | None) -> bool:
    if next_segment is None:
        return False

    text = normalize_text(str(current.get("text", "")))
    if len(text) >= 8:
        return False

    if is_noise_text(text):
        return False

    duration = float(current.get("end_time", 0.0)) - float(current.get("start_time", 0.0))
    if duration > 2.0:
        return False

    return text.endswith(("，", "、", ",", "：", ":")) or text.startswith(CONNECTIVE_PREFIXES)


def build_sentence_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    index = 0
    while index < len(segments):
        current = dict(segments[index])
        current["text"] = normalize_text(str(current.get("text", "")))

        next_segment = dict(segments[index + 1]) if index + 1 < len(segments) else None
        if next_segment is not None:
            next_segment["text"] = normalize_text(str(next_segment.get("text", "")))

        if should_merge_short_segment(current, next_segment):
            merged = {
                "start_time": float(current.get("start_time", 0.0)),
                "end_time": float(next_segment.get("end_time", current.get("end_time", 0.0))),
                "text": f"{current['text']}{next_segment['text']}",
                "confidence": min(
                    float(current.get("confidence", 1.0)),
                    float(next_segment.get("confidence", 1.0)),
                ),
                "source": current.get("source") or next_segment.get("source") or "unknown",
            }
            cleaned.append(merged)
            index += 2
            continue

        cleaned.append(current)
        index += 1

    return [item for item in cleaned if not is_noise_text(str(item.get("text", "")))]
