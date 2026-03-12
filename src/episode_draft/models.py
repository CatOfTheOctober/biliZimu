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
class QuoteAnchor:
    quote_id: str
    sentence_id: str
    start: float
    end: float
    text: str
    confidence: float
    reason: str


@dataclass
class TopicSegment:
    segment_id: str
    start: float
    end: float
    start_sentence_id: str
    end_sentence_id: str
    segment_summary: str
    retrieval_keywords: list[str] = field(default_factory=list)
    host_view_summary: str = ""
    quote_anchors: list[QuoteAnchor] = field(default_factory=list)
    angle_type: str = "fact_update"
    segment_role: str = "core_argument"
    subscope_label: str = ""
    sentence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    review_status: str = "needs_review"


@dataclass
class NewsTopic:
    topic_id: str
    canonical_topic: str
    tracking_scope: str
    retrieval_keywords: list[str] = field(default_factory=list)
    host_overall_view_summary: str = ""
    segments: list[TopicSegment] = field(default_factory=list)
    review_status: str = "needs_review"
    confidence: float = 0.0


@dataclass
class ReviewFlag:
    review_id: str
    review_type: str
    target_id: str
    reason: str
    candidate_options: list[str] = field(default_factory=list)


@dataclass
class ModelRun:
    stage: str
    backend: str
    target_id: str
    status: str = "completed"
    reason: str = ""
    confidence: float | None = None


@dataclass
class EpisodeDraft:
    schema_version: str
    source_bundle_id: str
    video: dict[str, Any]
    selected_track: dict[str, Any]
    processing: dict[str, Any]
    sentence_units: list[SentenceUnit] = field(default_factory=list)
    news_topics: list[NewsTopic] = field(default_factory=list)
    orphan_transition_sentence_ids: list[str] = field(default_factory=list)
    review_flags: list[ReviewFlag] = field(default_factory=list)
    model_runs: list[ModelRun] = field(default_factory=list)
