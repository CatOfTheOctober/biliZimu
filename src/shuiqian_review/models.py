"""Data models and validation for single-episode review packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .rules import (
    ALLOWED_EVIDENCE_STATUSES,
    ALLOWED_TRANSCRIPT_STATUSES,
    SOURCE_TYPE_MAINSTREAM,
    SOURCE_TYPE_OFFICIAL,
    TIMELINE_HARD_MIN,
    TIMELINE_RECOMMENDED_MAX,
    TIMELINE_RECOMMENDED_MIN,
    classify_source,
)


@dataclass
class ValidationIssue:
    level: str
    path: str
    message: str


@dataclass
class Segment:
    title: str
    start: str
    end: str
    summary: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Segment":
        return cls(
            title=data["title"],
            start=data["start"],
            end=data["end"],
            summary=data["summary"],
        )


@dataclass
class SourceEvidence:
    source_name: str
    source_type: str
    source_url: str
    source_label: str
    published_date: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceEvidence":
        return cls(
            source_name=data["source_name"],
            source_type=data["source_type"],
            source_url=data["source_url"],
            source_label=data["source_label"],
            published_date=data["published_date"],
        )


@dataclass
class TimelineEvent:
    date: str
    event: str
    source: SourceEvidence
    relation_to_host_view: str
    relevance_note: str
    verified: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimelineEvent":
        return cls(
            date=data["date"],
            event=data["event"],
            source=SourceEvidence.from_dict(data["source"]),
            relation_to_host_view=data["relation_to_host_view"],
            relevance_note=data["relevance_note"],
            verified=bool(data.get("verified", True)),
        )


@dataclass
class ClipCandidate:
    start: str
    end: str
    usage_note: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClipCandidate":
        return cls(
            start=data["start"],
            end=data["end"],
            usage_note=data["usage_note"],
        )


@dataclass
class NewsCard:
    title: str
    direct_scope: str
    original_background: str
    host_quote: str
    host_view_summary: str
    current_status: str
    evidence_status: str
    allowed_sources_used: list[str]
    timeline: list[TimelineEvent] = field(default_factory=list)
    clip_candidates: list[ClipCandidate] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NewsCard":
        return cls(
            title=data["title"],
            direct_scope=data["direct_scope"],
            original_background=data["original_background"],
            host_quote=data["host_quote"],
            host_view_summary=data["host_view_summary"],
            current_status=data["current_status"],
            evidence_status=data["evidence_status"],
            allowed_sources_used=list(data.get("allowed_sources_used", [])),
            timeline=[TimelineEvent.from_dict(item) for item in data.get("timeline", [])],
            clip_candidates=[ClipCandidate.from_dict(item) for item in data.get("clip_candidates", [])],
        )


@dataclass
class EpisodeCard:
    title: str
    air_date: str
    source_url: str
    transcript_status: str
    transcript_excerpt: str
    news_summary: str
    recording_cutoff_date: str
    segments: list[Segment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodeCard":
        return cls(
            title=data["title"],
            air_date=data["air_date"],
            source_url=data["source_url"],
            transcript_status=data["transcript_status"],
            transcript_excerpt=data["transcript_excerpt"],
            news_summary=data["news_summary"],
            recording_cutoff_date=data["recording_cutoff_date"],
            segments=[Segment.from_dict(item) for item in data.get("segments", [])],
        )


@dataclass
class EpisodePackage:
    project_title: str
    source_policy: str
    episode: EpisodeCard
    news_items: list[NewsCard]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodePackage":
        return cls(
            project_title=data["project_title"],
            source_policy=data["source_policy"],
            episode=EpisodeCard.from_dict(data["episode"]),
            news_items=[NewsCard.from_dict(item) for item in data.get("news_items", [])],
        )

    def validate(self) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_episode())
        if not self.news_items:
            issues.append(ValidationIssue("error", "news_items", "at_least_one_news_item_required"))
        for idx, news in enumerate(self.news_items):
            issues.extend(self._validate_news(news, idx))
        return issues

    def _validate_episode(self) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if self.episode.transcript_status not in ALLOWED_TRANSCRIPT_STATUSES:
            issues.append(
                ValidationIssue(
                    "error",
                    "episode.transcript_status",
                    f"invalid_transcript_status:{self.episode.transcript_status}",
                )
            )
        for field_name, value in (
            ("episode.air_date", self.episode.air_date),
            ("episode.recording_cutoff_date", self.episode.recording_cutoff_date),
        ):
            try:
                date.fromisoformat(value)
            except ValueError:
                issues.append(ValidationIssue("error", field_name, "invalid_iso_date"))
        if not self.episode.segments:
            issues.append(ValidationIssue("warning", "episode.segments", "no_segments_defined"))
        return issues

    def _validate_news(self, news: NewsCard, idx: int) -> list[ValidationIssue]:
        path = f"news_items[{idx}]"
        issues: list[ValidationIssue] = []

        if not news.host_quote.strip():
            issues.append(ValidationIssue("error", f"{path}.host_quote", "host_quote_required"))

        if news.evidence_status not in ALLOWED_EVIDENCE_STATUSES:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{path}.evidence_status",
                    f"invalid_evidence_status:{news.evidence_status}",
                )
            )

        timeline_count = len(news.timeline)
        if timeline_count < TIMELINE_HARD_MIN:
            issues.append(ValidationIssue("error", f"{path}.timeline", "at_least_one_timeline_event_required"))
        elif timeline_count < TIMELINE_RECOMMENDED_MIN:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"{path}.timeline",
                    f"timeline_events_below_recommended_min:{timeline_count}",
                )
            )
        elif timeline_count > TIMELINE_RECOMMENDED_MAX:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"{path}.timeline",
                    f"timeline_events_above_recommended_max:{timeline_count}",
                )
            )

        if not news.allowed_sources_used:
            issues.append(ValidationIssue("warning", f"{path}.allowed_sources_used", "no_source_summary_tags"))

        if news.evidence_status == "insufficient_public_info" and timeline_count > 0:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"{path}.evidence_status",
                    "marked_insufficient_public_info_review_timeline_manually",
                )
            )

        for event_idx, event in enumerate(news.timeline):
            issues.extend(self._validate_timeline_event(event, idx, event_idx))
        return issues

    def _validate_timeline_event(
        self,
        event: TimelineEvent,
        news_idx: int,
        event_idx: int,
    ) -> list[ValidationIssue]:
        path = f"news_items[{news_idx}].timeline[{event_idx}]"
        issues: list[ValidationIssue] = []
        try:
            date.fromisoformat(event.date)
        except ValueError:
            issues.append(ValidationIssue("error", f"{path}.date", "invalid_iso_date"))
        try:
            date.fromisoformat(event.source.published_date)
        except ValueError:
            issues.append(ValidationIssue("error", f"{path}.source.published_date", "invalid_iso_date"))

        decision = classify_source(
            event.source.source_name,
            event.source.source_type,
            event.source.source_url,
        )
        if not decision.allowed:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{path}.source",
                    f"source_not_allowed:{decision.reason}",
                )
            )

        if event.source.source_type not in {SOURCE_TYPE_OFFICIAL, SOURCE_TYPE_MAINSTREAM}:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{path}.source.source_type",
                    "source_type_must_be_official_or_mainstream_media",
                )
            )

        if not event.relation_to_host_view.strip():
            issues.append(ValidationIssue("warning", f"{path}.relation_to_host_view", "missing_relation_summary"))
        if not event.relevance_note.strip():
            issues.append(ValidationIssue("warning", f"{path}.relevance_note", "missing_direct_scope_note"))
        if not event.verified:
            issues.append(ValidationIssue("warning", f"{path}.verified", "timeline_event_not_manually_verified"))
        return issues
