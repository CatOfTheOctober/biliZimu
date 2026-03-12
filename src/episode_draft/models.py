"""Data models for the second-stage episode drafting pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SentenceUnit:
    sentence_id: str
    start: float
    end: float
    text: str
    block_candidate_id: str | None
    topic_hint: str
    sentence_type: str
    is_host_commentary: bool
    confidence: float
    review_status: str


@dataclass
class HostQuoteCandidate:
    quote_id: str
    start: float
    end: float
    text: str
    confidence: float
    reason: str


@dataclass
class NewsBlock:
    block_id: str
    start: float
    end: float
    title_candidate: str
    direct_scope_candidate: str
    background_summary: str
    host_view_summary_candidate: str
    host_quote_candidates: list[HostQuoteCandidate] = field(default_factory=list)
    sentence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    review_status: str = "needs_review"


@dataclass
class PendingReview:
    review_id: str
    review_type: str
    target_id: str
    reason: str
    candidate_options: list[str] = field(default_factory=list)


@dataclass
class EpisodeDraft:
    schema_version: str
    source_bundle_id: str
    video: dict[str, Any]
    selected_track: dict[str, Any]
    processing: dict[str, Any]
    sentence_units: list[SentenceUnit] = field(default_factory=list)
    news_blocks: list[NewsBlock] = field(default_factory=list)
    pending_reviews: list[PendingReview] = field(default_factory=list)
