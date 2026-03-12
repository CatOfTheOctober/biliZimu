"""Review flag helpers for EpisodeDraft generation."""

from __future__ import annotations

from .models import NewsBlock, PendingReview, SentenceUnit


def build_sentence_review(sentence: SentenceUnit, review_id: int) -> PendingReview | None:
    if sentence.review_status != "needs_review":
        return None
    return PendingReview(
        review_id=f"review_{review_id:03d}",
        review_type="sentence_assignment",
        target_id=sentence.sentence_id,
        reason="sentence_confidence_low_or_topic_ambiguous",
        candidate_options=[sentence.block_candidate_id] if sentence.block_candidate_id else [],
    )


def build_block_reviews(block: NewsBlock, review_id_start: int) -> list[PendingReview]:
    reviews: list[PendingReview] = []
    next_id = review_id_start

    if block.review_status == "needs_review":
        reviews.append(
            PendingReview(
                review_id=f"review_{next_id:03d}",
                review_type="news_block",
                target_id=block.block_id,
                reason="block_boundary_or_summary_requires_confirmation",
                candidate_options=[],
            )
        )
        next_id += 1

    if not block.host_quote_candidates:
        reviews.append(
            PendingReview(
                review_id=f"review_{next_id:03d}",
                review_type="host_quote",
                target_id=block.block_id,
                reason="no_host_quote_candidate_detected",
                candidate_options=[],
            )
        )

    return reviews
