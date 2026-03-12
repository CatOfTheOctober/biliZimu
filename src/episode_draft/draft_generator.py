"""Orchestrator for TranscriptBundle -> EpisodeDraft."""

from __future__ import annotations

from datetime import datetime, timezone

from .block_builder import similarity

from .block_builder import assign_blocks
from .io_utils import load_bundle
from .model_backend import AnalysisBackend, get_backend
from .models import EpisodeDraft, NewsTopic, SentenceUnit, TopicSegment
from .review_flags import build_segment_reviews, build_sentence_review, build_topic_reviews
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
    analysis_result = backend.analyze_sentences([item["text"] for item in segments])
    sentence_units = _build_sentence_units(segments, analysis_result.items)

    grouped, sentence_review_ids = assign_blocks(sentence_units)
    segment_candidates: list[dict] = []
    model_runs = list(analysis_result.model_runs)
    orphan_transition_sentence_ids: list[str] = []

    for index, block_sentences in enumerate(grouped, start=1):
        segment_id = f"segment_{index:02d}"
        for sentence in block_sentences:
            sentence.block_candidate_id = segment_id
            if sentence.sentence_id in sentence_review_ids:
                sentence.review_status = "needs_review"

        segment_result = backend.summarize_segment(block_sentences, segment_id)
        model_runs.extend(segment_result.model_runs)

        if _is_orphan_transition(segment_result.data, block_sentences):
            orphan_transition_sentence_ids.extend(item.sentence_id for item in block_sentences)
            for sentence in block_sentences:
                sentence.block_candidate_id = None
                sentence.review_status = "skipped"
            continue

        segment_candidates.append(segment_result.data)

    topic_merge_result = backend.merge_topics(segment_candidates)
    model_runs.extend(topic_merge_result.model_runs)
    focused_topics = _focus_topics(segment_candidates, topic_merge_result.data.get("topics", []))
    news_topics = _build_topics(segment_candidates, focused_topics)
    review_flags = _build_review_flags(sentence_units, news_topics)

    return EpisodeDraft(
        schema_version="2.1",
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
            "news_topic_count": len(news_topics),
            "topic_segment_count": sum(len(topic.segments) for topic in news_topics),
        },
        sentence_units=sentence_units,
        news_topics=news_topics,
        orphan_transition_sentence_ids=orphan_transition_sentence_ids,
        review_flags=review_flags,
        model_runs=model_runs,
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


def _is_orphan_transition(segment_data: dict, block_sentences: list[SentenceUnit]) -> bool:
    if segment_data.get("angle_type") != "transition":
        return False
    return all(item.sentence_type == "transition" for item in block_sentences)


def _build_topics(segment_candidates: list[dict], merged_topics: list[dict]) -> list[NewsTopic]:
    segment_lookup = {item["segment_id"]: item for item in segment_candidates}
    topics: list[NewsTopic] = []

    for topic in merged_topics:
        segments: list[TopicSegment] = []
        for segment_id in topic.get("segment_ids", []):
            segment = segment_lookup.get(segment_id)
            if segment is None:
                continue
            segments.append(
                TopicSegment(
                    segment_id=segment["segment_id"],
                    start=float(segment["start"]),
                    end=float(segment["end"]),
                    start_sentence_id=str(segment["start_sentence_id"]),
                    end_sentence_id=str(segment["end_sentence_id"]),
                    segment_summary=str(segment["segment_summary"]),
                    retrieval_keywords=list(segment.get("retrieval_keywords", [])),
                    host_view_summary=str(segment.get("host_view_summary", "")),
                    quote_anchors=list(segment.get("quote_anchors", [])),
                    angle_type=str(segment.get("angle_type", "fact_update")),
                    segment_role=str(segment.get("segment_role", "core_argument")),
                    subscope_label=str(segment.get("subscope_label", "")),
                    sentence_ids=list(segment.get("sentence_ids", [])),
                    confidence=float(segment.get("confidence", 0.0)),
                    review_status=str(segment.get("review_status", "needs_review")),
                )
            )

        topics.append(
            NewsTopic(
                topic_id=str(topic.get("topic_id", f"topic_{len(topics) + 1:02d}")),
                canonical_topic=str(topic.get("canonical_topic", "")),
                tracking_scope=str(topic.get("tracking_scope", "")),
                retrieval_keywords=list(topic.get("retrieval_keywords", [])),
                host_overall_view_summary=str(topic.get("host_overall_view_summary", "")),
                segments=sorted(segments, key=lambda item: item.start),
                review_status=str(topic.get("review_status", "needs_review")),
                confidence=float(topic.get("confidence", 0.0)),
            )
        )

    return topics


def _build_review_flags(sentence_units: list[SentenceUnit], news_topics: list[NewsTopic]):
    review_flags = []
    review_id = 1

    for sentence in sentence_units:
        item = build_sentence_review(sentence, review_id)
        if item is not None:
            review_flags.append(item)
            review_id += 1

    for topic in news_topics:
        for segment in topic.segments:
            segment_reviews = build_segment_reviews(segment, review_id)
            review_flags.extend(segment_reviews)
            review_id += len(segment_reviews)

        topic_reviews = build_topic_reviews(topic, review_id)
        review_flags.extend(topic_reviews)
        review_id += len(topic_reviews)

    return review_flags


def _focus_topics(segment_candidates: list[dict], merged_topics: list[dict]) -> list[dict]:
    segment_lookup = {item["segment_id"]: dict(item) for item in segment_candidates}
    topics = [_normalize_topic(topic, segment_lookup, index) for index, topic in enumerate(merged_topics, start=1)]
    topics = [topic for topic in topics if topic["segment_ids"]]
    if not topics:
        return []

    primary_topics = [topic for topic in topics if not _topic_should_attach(topic)]
    if not primary_topics:
        primary_topics = [max(topics, key=lambda item: len(item["segment_ids"]))]

    attached_ids = {topic["topic_id"] for topic in primary_topics}
    for topic in topics:
        if topic["topic_id"] in attached_ids:
            continue
        target = _pick_attachment_target(topic, primary_topics)
        if target is None:
            primary_topics.append(topic)
            attached_ids.add(topic["topic_id"])
            continue
        _attach_topic(topic, target)

    primary_topics = sorted(primary_topics, key=_topic_start_time)
    if len(primary_topics) > 3:
        primary_topics = _compress_topics(primary_topics)
    primary_topics = _merge_adjacent_topics(primary_topics)
    _rebalance_supporting_segments(primary_topics, segment_lookup)
    primary_topics = [topic for topic in primary_topics if topic["segment_ids"]]

    for topic in primary_topics:
        _refresh_topic(topic, segment_lookup)

    return primary_topics


def _normalize_topic(topic: dict, segment_lookup: dict[str, dict], index: int) -> dict:
    segment_ids = [segment_id for segment_id in topic.get("segment_ids", []) if segment_id in segment_lookup]
    starts = [float(segment_lookup[segment_id]["start"]) for segment_id in segment_ids]
    ends = [float(segment_lookup[segment_id]["end"]) for segment_id in segment_ids]
    return {
        "topic_id": str(topic.get("topic_id", f"topic_{index:02d}")),
        "canonical_topic": str(topic.get("canonical_topic", "")).strip(),
        "tracking_scope": str(topic.get("tracking_scope", "")).strip(),
        "retrieval_keywords": [str(item) for item in topic.get("retrieval_keywords", [])],
        "host_overall_view_summary": str(topic.get("host_overall_view_summary", "")).strip(),
        "segment_ids": segment_ids,
        "review_status": str(topic.get("review_status", "needs_review")),
        "confidence": float(topic.get("confidence", 0.0)),
        "start": min(starts) if starts else 0.0,
        "end": max(ends) if ends else 0.0,
        "segment_roles": [str(segment_lookup[segment_id].get("segment_role", "core_argument")) for segment_id in segment_ids],
    }


def _topic_should_attach(topic: dict) -> bool:
    canonical = topic["canonical_topic"]
    segments = topic["segment_ids"]
    if not segments:
        return True
    if all(role in {"supporting_context", "transition"} for role in topic.get("segment_roles", [])):
        return True
    if len(segments) == 1 and _looks_like_supporting_topic(canonical):
        return True
    return False


def _pick_attachment_target(topic: dict, primary_topics: list[dict]) -> dict | None:
    best_topic = None
    best_score = -1.0
    for candidate in primary_topics:
        score = _topic_attachment_score(topic, candidate)
        if score > best_score:
            best_score = score
            best_topic = candidate
    if best_topic is None:
        return None
    if best_score >= 0.16 or len(primary_topics) >= 3:
        return best_topic
    return None


def _topic_attachment_score(left: dict, right: dict) -> float:
    title_score = similarity(left["canonical_topic"], right["canonical_topic"])
    left_keywords = set(left.get("retrieval_keywords", []))
    right_keywords = set(right.get("retrieval_keywords", []))
    keyword_score = len(left_keywords & right_keywords) / max(len(left_keywords | right_keywords), 1)
    time_gap = abs(_topic_start_time(left) - _topic_end_time(right))
    time_bonus = 0.12 if time_gap <= 180 else 0.0
    return max(title_score, keyword_score + time_bonus)


def _attach_topic(source: dict, target: dict) -> None:
    target["segment_ids"] = sorted(set(target["segment_ids"] + source["segment_ids"]))
    target["retrieval_keywords"] = _merge_unique(target["retrieval_keywords"], source["retrieval_keywords"], limit=16)
    target["host_overall_view_summary"] = _merge_text(
        target["host_overall_view_summary"],
        source["host_overall_view_summary"],
        limit=360,
    )
    target["confidence"] = round((target["confidence"] + source["confidence"]) / 2, 3)
    if source["review_status"] == "needs_review":
        target["review_status"] = "needs_review"


def _compress_topics(topics: list[dict]) -> list[dict]:
    topics = list(topics)
    while len(topics) > 3:
        singleton_candidates = [topic for topic in topics if len(topic["segment_ids"]) == 1]
        if not singleton_candidates:
            break
        source = min(singleton_candidates, key=lambda item: item["confidence"])
        remaining = [topic for topic in topics if topic["topic_id"] != source["topic_id"]]
        target = _pick_attachment_target(source, remaining)
        if target is None:
            break
        _attach_topic(source, target)
        topics = remaining
    return sorted(topics, key=_topic_start_time)


def _merge_adjacent_topics(topics: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for topic in sorted(topics, key=_topic_start_time):
        if merged and _should_merge_neighbor_topics(merged[-1], topic):
            _attach_topic(topic, merged[-1])
            continue
        merged.append(topic)
    return merged


def _should_merge_neighbor_topics(left: dict, right: dict) -> bool:
    gap = max(_topic_start_time(right) - _topic_end_time(left), 0.0)
    if gap > 30.0:
        return False
    left_roles = set(left.get("segment_roles", []))
    right_roles = set(right.get("segment_roles", []))
    if "proposal" in left_roles and "proposal" in right_roles:
        return True
    if left["canonical_topic"].startswith("中国") and right["canonical_topic"].startswith("中国"):
        return True
    return _topic_attachment_score(left, right) >= 0.24


def _rebalance_supporting_segments(topics: list[dict], segment_lookup: dict[str, dict]) -> None:
    ordered = sorted(topics, key=_topic_start_time)
    for index in range(1, len(ordered)):
        previous = ordered[index - 1]
        current = ordered[index]
        anchor_segment_ids = [
            segment_id
            for segment_id in current["segment_ids"]
            if segment_lookup[segment_id].get("segment_role") in {"core_argument", "proposal"}
        ]
        if not anchor_segment_ids:
            continue
        anchor_start = min(float(segment_lookup[segment_id]["start"]) for segment_id in anchor_segment_ids)
        moved_ids: list[str] = []
        for segment_id in current["segment_ids"]:
            segment = segment_lookup[segment_id]
            if segment.get("segment_role") != "supporting_context":
                continue
            if float(segment.get("end", 0.0)) > anchor_start:
                continue
            previous_score = _segment_topic_score(segment, previous)
            current_score = _segment_topic_score(segment, current)
            if previous_score >= current_score:
                previous["segment_ids"].append(segment_id)
                moved_ids.append(segment_id)
        if moved_ids:
            current["segment_ids"] = [segment_id for segment_id in current["segment_ids"] if segment_id not in moved_ids]
            previous["segment_ids"] = sorted(set(previous["segment_ids"]))
            previous["start"] = min(float(segment_lookup[segment_id]["start"]) for segment_id in previous["segment_ids"])
            previous["end"] = max(float(segment_lookup[segment_id]["end"]) for segment_id in previous["segment_ids"])
            previous["segment_roles"] = [str(segment_lookup[segment_id].get("segment_role", "core_argument")) for segment_id in previous["segment_ids"]]
            if current["segment_ids"]:
                current["start"] = min(float(segment_lookup[segment_id]["start"]) for segment_id in current["segment_ids"])
                current["end"] = max(float(segment_lookup[segment_id]["end"]) for segment_id in current["segment_ids"])
                current["segment_roles"] = [str(segment_lookup[segment_id].get("segment_role", "core_argument")) for segment_id in current["segment_ids"]]


def _refresh_topic(topic: dict, segment_lookup: dict[str, dict]) -> None:
    segments = [segment_lookup[segment_id] for segment_id in topic["segment_ids"] if segment_id in segment_lookup]
    if not segments:
        return

    primary_segments = [segment for segment in segments if segment.get("segment_role") in {"core_argument", "proposal"}]
    anchor_segments = primary_segments or segments
    best_topic = max(anchor_segments, key=lambda item: len(str(item.get("topic_candidate", ""))))
    topic["canonical_topic"] = topic["canonical_topic"] or str(best_topic.get("topic_candidate", ""))
    topic["tracking_scope"] = topic["tracking_scope"] or str(best_topic.get("tracking_scope_candidate", ""))
    topic["retrieval_keywords"] = _merge_unique(*(segment.get("retrieval_keywords", []) for segment in segments), limit=16)
    topic["host_overall_view_summary"] = _merge_text(
        *(str(segment.get("host_view_summary", "")) for segment in segments),
        limit=360,
    )
    topic["confidence"] = round(
        sum(float(segment.get("confidence", 0.0)) for segment in segments) / max(len(segments), 1),
        3,
    )
    topic["start"] = min(float(segment.get("start", 0.0)) for segment in segments)
    topic["end"] = max(float(segment.get("end", 0.0)) for segment in segments)
    topic["segment_roles"] = [str(segment.get("segment_role", "core_argument")) for segment in segments]
    if any(str(segment.get("review_status", "needs_review")) == "needs_review" for segment in segments):
        topic["review_status"] = "needs_review"


def _topic_start_time(topic: dict) -> float:
    return float(topic.get("start", 0.0))


def _topic_end_time(topic: dict) -> float:
    return float(topic.get("end", 0.0))


def _looks_like_supporting_topic(text: str) -> bool:
    lowered = text.strip()
    return any(marker in lowered for marker in ("记忆", "印象", "回忆", "观感", "见闻", "名言", "宣传片", "开幕式"))


def _segment_topic_score(segment: dict, topic: dict) -> float:
    title_score = similarity(str(segment.get("topic_candidate", "")), topic["canonical_topic"])
    segment_keywords = set(segment.get("retrieval_keywords", []))
    topic_keywords = set(topic.get("retrieval_keywords", []))
    keyword_score = len(segment_keywords & topic_keywords) / max(len(segment_keywords | topic_keywords), 1)
    if any(keyword in topic_keywords for keyword in segment_keywords):
        keyword_score += 0.1
    return max(title_score, keyword_score)


def _merge_unique(*groups: list[str], limit: int) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for item in group:
            if item and item not in merged:
                merged.append(str(item))
    return merged[:limit]


def _merge_text(*values: str, limit: int) -> str:
    merged: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in merged:
            merged.append(text)
    return " ".join(merged)[:limit]
