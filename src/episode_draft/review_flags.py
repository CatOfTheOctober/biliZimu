"""Review flag helpers for EpisodeDraft generation."""

from __future__ import annotations

from .models import NewsTopic, ReviewFlag, SentenceUnit, TopicSegment


def build_sentence_review(sentence: SentenceUnit, review_id: int) -> ReviewFlag | None:
    if sentence.review_status != "needs_review":
        return None
    return ReviewFlag(
        review_id=f"review_{review_id:03d}",
        review_type="sentence_assignment",
        target_id=sentence.sentence_id,
        reason="sentence_confidence_low_or_topic_ambiguous",
        candidate_options=[sentence.block_candidate_id] if sentence.block_candidate_id else [],
    )


def build_segment_reviews(segment: TopicSegment, review_id_start: int) -> list[ReviewFlag]:
    reviews: list[ReviewFlag] = []
    next_id = review_id_start

    if segment.review_status == "needs_review":
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="topic_segment",
                target_id=segment.segment_id,
                reason="segment_boundary_or_summary_requires_confirmation",
                candidate_options=[],
            )
        )
        next_id += 1

    if not segment.quote_anchors:
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="quote_anchor",
                target_id=segment.segment_id,
                reason="no_quote_anchor_detected",
                candidate_options=[],
            )
        )
        next_id += 1

    if len(segment.sentence_ids) < 3:
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="segment_size",
                target_id=segment.segment_id,
                reason="segment_too_short_for_confident_review",
                candidate_options=[],
            )
        )
        next_id += 1

    if segment.segment_role == "supporting_context" and segment.angle_type in {"host_judgment", "mechanism_explanation"}:
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="segment_role",
                target_id=segment.segment_id,
                reason="supporting_context_contains_strong_argument_and_should_be_checked",
                candidate_options=[],
            )
        )
        next_id += 1

    if len(segment.sentence_ids) >= 80 and segment.segment_role != "transition":
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="segment_boundary",
                target_id=segment.segment_id,
                reason="segment_is_long_and_may_mix_diagnosis_and_proposal",
                candidate_options=[],
            )
        )

    return reviews


def build_topic_reviews(topic: NewsTopic, review_id_start: int) -> list[ReviewFlag]:
    reviews: list[ReviewFlag] = []
    next_id = review_id_start

    if topic.review_status == "needs_review":
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="news_topic",
                target_id=topic.topic_id,
                reason="topic_grouping_or_tracking_scope_requires_confirmation",
                candidate_options=[segment.segment_id for segment in topic.segments],
            )
        )
        next_id += 1

    if not topic.retrieval_keywords:
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="topic_keywords",
                target_id=topic.topic_id,
                reason="topic_keyword_extraction_missing",
                candidate_options=[],
            )
        )
        next_id += 1

    if len(topic.segments) == 1 and _looks_like_supporting_title(topic.canonical_topic):
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="news_topic",
                target_id=topic.topic_id,
                reason="topic_title_looks_like_supporting_context",
                candidate_options=[segment.segment_id for segment in topic.segments],
            )
        )
        next_id += 1

    if topic.segments and all(segment.segment_role == "supporting_context" for segment in topic.segments):
        reviews.append(
            ReviewFlag(
                review_id=f"review_{next_id:03d}",
                review_type="news_topic",
                target_id=topic.topic_id,
                reason="supporting_segments_should_not_form_standalone_topic",
                candidate_options=[segment.segment_id for segment in topic.segments],
            )
        )

    return reviews


def _looks_like_supporting_title(text: str) -> bool:
    lowered = text.strip()
    return any(marker in lowered for marker in ("记忆", "印象", "回忆", "观感", "见闻", "名言", "宣传片", "开幕式"))
