"""Orchestrator for TranscriptBundle -> EpisodeDraft."""

from __future__ import annotations

from datetime import datetime, timezone

from .block_builder import assign_blocks
from .io_utils import load_bundle
from .model_backend import AnalysisBackend, get_backend
from .models import EpisodeDraft, NewsBlock, SentenceUnit
from .review_flags import build_block_reviews, build_sentence_review
from .sentence_processor import build_sentence_segments


def generate_draft(bundle_dir: str, backend_mode: str = "auto") -> EpisodeDraft:
    loaded = load_bundle(bundle_dir)
    transcript_bundle = loaded["transcript_bundle"]
    manifest = loaded["manifest"]
    backend = _resolve_backend(backend_mode)

    selected_track_id = transcript_bundle["selected_track"]
    tracks = transcript_bundle.get("tracks", [])
    track = next((item for item in tracks if item.get("track_id") == selected_track_id), None)
    if track is None:
        raise ValueError(f"selected_track_not_found:{selected_track_id}")

    segments = build_sentence_segments(track.get("segments", []))
    analyses = backend.analyze_sentences([item["text"] for item in segments])
    sentence_units = _build_sentence_units(segments, analyses)

    grouped, sentence_review_ids = assign_blocks(sentence_units)
    blocks = _build_news_blocks(grouped, backend, sentence_review_ids)
    pending_reviews = _build_pending_reviews(sentence_units, blocks)

    return EpisodeDraft(
        schema_version="1.0",
        source_bundle_id=manifest.get("bundle_id") or loaded["paths"]["bundle_dir"].name,
        video=transcript_bundle.get("video", {}),
        selected_track={
            "track_id": track.get("track_id"),
            "track_type": track.get("track_type"),
            "source": track.get("source"),
            "label": track.get("label"),
            "language": track.get("language"),
            "segment_count": len(sentence_units),
        },
        processing={
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "backend": backend.name,
            "source_bundle_dir": str(loaded["paths"]["bundle_dir"]),
            "sentence_count": len(sentence_units),
            "news_block_count": len(blocks),
        },
        sentence_units=sentence_units,
        news_blocks=blocks,
        pending_reviews=pending_reviews,
    )


def _resolve_backend(backend_mode: str) -> AnalysisBackend:
    try:
        return get_backend(backend_mode)
    except Exception:
        return get_backend("heuristic")


def _build_sentence_units(segments: list[dict], analyses: list) -> list[SentenceUnit]:
    sentence_units: list[SentenceUnit] = []
    for index, (segment, analysis) in enumerate(zip(segments, analyses), start=1):
        review_status = "ready" if analysis.confidence >= 0.55 else "needs_review"
        sentence_units.append(
            SentenceUnit(
                sentence_id=f"s{index:03d}",
                start=float(segment["start_time"]),
                end=float(segment["end_time"]),
                text=segment["text"],
                block_candidate_id=None,
                topic_hint=analysis.topic_hint,
                sentence_type=analysis.sentence_type,
                is_host_commentary=analysis.is_host_commentary,
                confidence=float(analysis.confidence),
                review_status=review_status,
            )
        )
    return sentence_units


def _build_news_blocks(
    grouped: list[list[SentenceUnit]],
    backend: AnalysisBackend,
    sentence_review_ids: set[str],
) -> list[NewsBlock]:
    blocks: list[NewsBlock] = []
    for index, block_sentences in enumerate(grouped, start=1):
        block_id = f"block_{index:02d}"
        for sentence in block_sentences:
            sentence.block_candidate_id = block_id
            if sentence.sentence_id in sentence_review_ids:
                sentence.review_status = "needs_review"

        summary = backend.summarize_block(block_sentences, block_id)
        block_review_status = "ready"
        if len(block_sentences) <= 1 or any(item.review_status == "needs_review" for item in block_sentences):
            block_review_status = "needs_review"

        blocks.append(
            NewsBlock(
                block_id=block_id,
                start=block_sentences[0].start,
                end=block_sentences[-1].end,
                title_candidate=str(summary.get("title_candidate", "")),
                direct_scope_candidate=str(summary.get("direct_scope_candidate", "")),
                background_summary=str(summary.get("background_summary", "")),
                host_view_summary_candidate=str(summary.get("host_view_summary_candidate", "")),
                host_quote_candidates=list(summary.get("host_quote_candidates", [])),
                sentence_ids=[item.sentence_id for item in block_sentences],
                confidence=float(summary.get("confidence", 0.5)),
                review_status=block_review_status,
            )
        )
    return blocks


def _build_pending_reviews(sentence_units: list[SentenceUnit], blocks: list[NewsBlock]):
    pending = []
    review_id = 1
    for sentence in sentence_units:
        item = build_sentence_review(sentence, review_id)
        if item is not None:
            pending.append(item)
            review_id += 1

    for block in blocks:
        block_reviews = build_block_reviews(block, review_id)
        pending.extend(block_reviews)
        review_id += len(block_reviews)
    return pending
