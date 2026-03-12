"""Backend abstraction for sentence, segment, and topic analysis."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Protocol

import requests

from .block_builder import similarity
from .env_utils import load_project_env
from .models import ModelRun, QuoteAnchor, SentenceUnit
from .prompts import (
    build_segment_extract_prompt,
    build_sentence_analysis_prompt,
    build_topic_merge_prompt,
)


COMMENTARY_MARKERS = (
    "我认为",
    "我觉得",
    "我看",
    "我最喜欢",
    "我听说",
    "我知道",
    "我想",
    "说明",
    "意味着",
    "问题在于",
    "问题就是",
    "本质上",
    "其实",
    "显然",
    "可以看到",
    "必须",
    "应该",
    "值得注意",
    "老观众都知道",
)

TRANSITION_MARKERS = (
    "接下来",
    "再说",
    "另外",
    "此外",
    "下面",
    "然后",
    "还有",
    "先说",
    "再看",
    "下一条",
)

NEWS_MARKERS = (
    "今天",
    "发布",
    "通报",
    "宣布",
    "报道",
    "表示",
    "出现",
    "项目",
    "学校",
    "企业",
    "债",
    "铁路",
    "教育",
    "房产",
    "城投",
)

STOP_PHRASES = {
    "这个",
    "那个",
    "就是",
    "不是",
    "我们",
    "你们",
    "他们",
    "今天",
    "现在",
    "这里",
    "已经",
    "因为",
    "所以",
    "如果",
}

ANGLE_TYPES = {
    "background",
    "fact_update",
    "host_judgment",
    "mechanism_explanation",
    "responsibility_focus",
    "macro_extension",
    "transition",
}

SEGMENT_ROLES = {
    "core_argument",
    "supporting_context",
    "proposal",
    "transition",
}

ANECDOTE_MARKERS = (
    "回忆",
    "印象",
    "我家",
    "我读大学",
    "第一次",
    "暑假",
    "小时候",
    "宣传片",
    "开幕式",
    "名言",
    "见闻",
)

PROPOSAL_MARKERS = (
    "结论很明显",
    "那就只能",
    "既然不能",
    "或许中国可以",
    "可以选一个",
    "建议",
    "所以真的",
    "唯一能够对应",
)


@dataclass
class SentenceAnalysis:
    sentence_type: str
    topic_hint: str
    confidence: float
    is_host_commentary: bool


@dataclass
class AnalysisBatchResult:
    items: list[SentenceAnalysis]
    model_runs: list[ModelRun]


@dataclass
class StructuredResult:
    data: dict[str, Any]
    model_runs: list[ModelRun]


class AnalysisBackend(Protocol):
    name: str

    def analyze_sentences(self, texts: list[str]) -> AnalysisBatchResult:
        ...

    def summarize_segment(self, sentences: list[SentenceUnit], segment_id: str) -> StructuredResult:
        ...

    def merge_topics(self, segments: list[dict[str, Any]]) -> StructuredResult:
        ...


class HeuristicBackend:
    name = "heuristic"

    def analyze_sentences(self, texts: list[str]) -> AnalysisBatchResult:
        items = [self._analyze_sentence(text) for text in texts]
        return AnalysisBatchResult(
            items=items,
            model_runs=[ModelRun(stage="sentence_analysis", backend=self.name, target_id="episode")],
        )

    def summarize_segment(self, sentences: list[SentenceUnit], segment_id: str) -> StructuredResult:
        factual = [item for item in sentences if item.sentence_type == "news_fact"]
        commentary = [item for item in sentences if item.is_host_commentary]
        primary = factual[0] if factual else sentences[0]

        topic_candidate = self._make_topic_candidate(primary.text)
        angle_type = self._infer_angle_type(sentences)
        segment_role = self._infer_segment_role(sentences, angle_type)
        segment_summary = self._summarize_sentences(factual[:3] or sentences[:3])
        host_view_summary = self._summarize_sentences(commentary[:2] or sentences[:2])
        retrieval_keywords = self._extract_keywords(sentences, topic_candidate)
        subscope_label = self._make_subscope_label(topic_candidate, angle_type, retrieval_keywords)
        tracking_scope_candidate = self._make_tracking_scope(topic_candidate, angle_type, subscope_label)
        quote_anchors = [
            QuoteAnchor(
                quote_id=f"{segment_id}_quote_{idx:02d}",
                sentence_id=item.sentence_id,
                start=item.start,
                end=item.end,
                text=item.text,
                confidence=item.confidence,
                reason="commentary_sentence",
            )
            for idx, item in enumerate(commentary[:2], start=1)
        ]

        confidence = round(sum(item.confidence for item in sentences) / max(len(sentences), 1), 3)
        review_status = "ready" if confidence >= 0.72 and quote_anchors else "needs_review"
        return StructuredResult(
            data={
                "segment_id": segment_id,
                "start": sentences[0].start,
                "end": sentences[-1].end,
                "start_sentence_id": sentences[0].sentence_id,
                "end_sentence_id": sentences[-1].sentence_id,
                "segment_summary": segment_summary,
                "retrieval_keywords": retrieval_keywords,
                "host_view_summary": host_view_summary,
                "quote_anchors": quote_anchors,
                "angle_type": angle_type,
                "segment_role": segment_role,
                "subscope_label": subscope_label,
                "topic_candidate": topic_candidate,
                "tracking_scope_candidate": tracking_scope_candidate,
                "sentence_ids": [item.sentence_id for item in sentences],
                "confidence": confidence,
                "review_status": review_status,
            },
            model_runs=[ModelRun(stage="segment_extract", backend=self.name, target_id=segment_id, confidence=confidence)],
        )

    def merge_topics(self, segments: list[dict[str, Any]]) -> StructuredResult:
        groups: list[dict[str, Any]] = []
        for segment in sorted(segments, key=lambda item: item["start"]):
            matched_group = None
            matched_score = 0.0
            for group in groups:
                score = self._topic_group_score(segment, group)
                if score > matched_score:
                    matched_score = score
                    matched_group = group

            if matched_group is not None and matched_score >= 0.42:
                matched_group["segments"].append(segment)
                matched_group["scores"].append(matched_score)
                continue

            groups.append({"segments": [segment], "scores": [segment["confidence"]]})

        topics: list[dict[str, Any]] = []
        for index, group in enumerate(groups, start=1):
            canonical_topic = self._canonicalize_topic(group["segments"])
            tracking_scope = self._canonicalize_scope(group["segments"], canonical_topic)
            keywords = self._merge_keywords(group["segments"])
            host_summary = self._merge_host_summaries(group["segments"])
            average_confidence = round(
                sum(segment["confidence"] for segment in group["segments"]) / max(len(group["segments"]), 1),
                3,
            )
            review_status = "ready"
            if average_confidence < 0.72 or any(segment["review_status"] == "needs_review" for segment in group["segments"]):
                review_status = "needs_review"

            topics.append(
                {
                    "topic_id": f"topic_{index:02d}",
                    "canonical_topic": canonical_topic,
                    "tracking_scope": tracking_scope,
                    "retrieval_keywords": keywords,
                    "host_overall_view_summary": host_summary,
                    "segment_ids": [segment["segment_id"] for segment in sorted(group["segments"], key=lambda item: item["start"])],
                    "review_status": review_status,
                    "confidence": average_confidence,
                }
            )

        return StructuredResult(
            data={"topics": topics},
            model_runs=[ModelRun(stage="topic_merge", backend=self.name, target_id="episode")],
        )

    def _analyze_sentence(self, text: str) -> SentenceAnalysis:
        normalized = text.strip()
        if any(normalized.startswith(marker) for marker in TRANSITION_MARKERS):
            return SentenceAnalysis(
                sentence_type="transition",
                topic_hint=self._infer_topic(normalized),
                confidence=0.62,
                is_host_commentary=False,
            )

        commentary_score = sum(1 for marker in COMMENTARY_MARKERS if marker in normalized)
        commentary_score += int(
            "我" in normalized and any(token in normalized for token in ("要", "看", "觉得", "认为", "喜欢", "知道", "想"))
        )
        news_score = sum(1 for marker in NEWS_MARKERS if marker in normalized)
        news_score += int(any(ch.isdigit() for ch in normalized))

        if commentary_score > news_score:
            return SentenceAnalysis(
                sentence_type="host_commentary",
                topic_hint=self._infer_topic(normalized),
                confidence=0.72,
                is_host_commentary=True,
            )

        if news_score > 0:
            return SentenceAnalysis(
                sentence_type="news_fact",
                topic_hint=self._infer_topic(normalized),
                confidence=0.68,
                is_host_commentary=False,
            )

        return SentenceAnalysis(
            sentence_type="transition",
            topic_hint=self._infer_topic(normalized),
            confidence=0.56,
            is_host_commentary=False,
        )

    def _infer_topic(self, text: str) -> str:
        compact = text.replace("，", " ").replace("。", " ").replace("：", " ").replace("、", " ")
        compact = compact.replace(",", " ").replace("?", " ")
        parts = [self._normalize_topic_phrase(item.strip()) for item in compact.split() if item.strip()]
        candidates = [item for item in parts if len(item) >= 2 and item not in STOP_PHRASES]
        return candidates[0] if candidates else self._normalize_topic_phrase(text)[:16]

    def _make_topic_candidate(self, text: str) -> str:
        phrase = self._normalize_topic_phrase(text)
        if len(phrase) <= 20:
            return phrase
        return phrase[:20].rstrip("，。！？；：,.!?;: ")

    def _normalize_topic_phrase(self, text: str) -> str:
        phrase = text.strip("，。！？；：,.!?;: ")
        phrase = re.sub(r"^(今天先说|先说|再说|再看|接下来聊|接下来|下面聊|下面|然后聊|然后|另外聊|另外|还有|最后聊|最后)", "", phrase)
        phrase = re.sub(r"^(我们看|我们说|说说|聊聊)", "", phrase)
        phrase = re.sub(r"^(说回|回到|回看|回|再说回)", "", phrase)
        first_clause = re.split(r"[，。！？；：,.!?;:]", phrase)[0].strip()
        return first_clause or phrase

    def _summarize_sentences(self, sentences: list[SentenceUnit]) -> str:
        parts = [item.text.strip() for item in sentences if item.text.strip()]
        if not parts:
            return ""
        summary = " ".join(parts[:2])
        return summary[:120].strip()

    def _extract_keywords(self, sentences: list[SentenceUnit], topic_candidate: str) -> list[str]:
        texts = [self._normalize_topic_phrase(item.text) for item in sentences]
        candidates: list[str] = []
        if topic_candidate:
            candidates.append(topic_candidate)

        for text in texts:
            for chunk in re.split(r"[，。！？；：,.!?;:、 ]+", text):
                chunk = chunk.strip()
                if len(chunk) < 2 or len(chunk) > 12:
                    continue
                if chunk in STOP_PHRASES:
                    continue
                candidates.append(chunk)

        seen: list[str] = []
        for candidate in candidates:
            if candidate not in seen:
                seen.append(candidate)
        return seen[:6]

    def _infer_angle_type(self, sentences: list[SentenceUnit]) -> str:
        text = "".join(item.text for item in sentences)
        commentary_count = sum(1 for item in sentences if item.is_host_commentary)
        factual_count = sum(1 for item in sentences if item.sentence_type == "news_fact")

        if all(item.sentence_type == "transition" for item in sentences):
            return "transition"
        if "官员" in text or "问责" in text or "责任" in text:
            return "responsibility_focus"
        if "全国" in text or "各地" in text or "整体" in text:
            return "macro_extension"
        if "本质" in text or "机制" in text or "意味着" in text:
            return "mechanism_explanation"
        if commentary_count >= factual_count and commentary_count > 0:
            return "host_judgment"
        if sentences and sentences[0].sentence_type == "news_fact":
            return "background"
        return "fact_update"

    def _infer_segment_role(self, sentences: list[SentenceUnit], angle_type: str) -> str:
        text = "".join(item.text for item in sentences)
        if angle_type == "transition":
            return "transition"
        if any(marker in text for marker in PROPOSAL_MARKERS):
            return "proposal"
        if any(marker in text for marker in ANECDOTE_MARKERS):
            return "supporting_context"
        if text.count("我") >= 3 and angle_type in {"background", "fact_update"}:
            return "supporting_context"
        return "core_argument"

    def _make_subscope_label(self, topic_candidate: str, angle_type: str, keywords: list[str]) -> str:
        anchor = keywords[0] if keywords else topic_candidate
        if angle_type == "responsibility_focus":
            return f"{anchor}责任后续"
        if angle_type == "macro_extension":
            return f"{anchor}扩展讨论"
        if angle_type == "mechanism_explanation":
            return f"{anchor}机制分析"
        return anchor

    def _make_tracking_scope(self, topic_candidate: str, angle_type: str, subscope_label: str) -> str:
        if angle_type == "responsibility_focus":
            return f"跟踪{subscope_label}相关责任主体后续公开信息"
        if angle_type == "macro_extension":
            return f"跟踪{subscope_label}相关宏观扩展与公开政策变化"
        return f"只跟踪{topic_candidate}相关公开进展"

    def _topic_group_score(self, segment: dict[str, Any], group: dict[str, Any]) -> float:
        group_topic = self._canonicalize_topic(group["segments"])
        title_score = similarity(segment["topic_candidate"], group_topic)
        group_keywords = set(self._merge_keywords(group["segments"]))
        segment_keywords = set(segment.get("retrieval_keywords", []))
        keyword_score = len(group_keywords & segment_keywords) / max(len(group_keywords | segment_keywords), 1)
        overlap_bonus = 0.2 if group_keywords & segment_keywords else 0.0

        group_angle_types = {item["angle_type"] for item in group["segments"]}
        if "macro_extension" in group_angle_types or segment["angle_type"] == "macro_extension":
            if segment["angle_type"] not in group_angle_types:
                return min(title_score, 0.25)
        if "responsibility_focus" in group_angle_types or segment["angle_type"] == "responsibility_focus":
            if segment["angle_type"] not in group_angle_types:
                return min(title_score, 0.25)

        return max(title_score, keyword_score + overlap_bonus)

    def _canonicalize_topic(self, segments: list[dict[str, Any]]) -> str:
        sorted_segments = sorted(segments, key=lambda item: item["start"])
        best = max(sorted_segments, key=lambda item: len(item["topic_candidate"]))
        return best["topic_candidate"]

    def _canonicalize_scope(self, segments: list[dict[str, Any]], canonical_topic: str) -> str:
        candidates = [item.get("tracking_scope_candidate", "") for item in segments if item.get("tracking_scope_candidate")]
        if candidates:
            longest = max(candidates, key=len)
            if len(candidates) == 1:
                return longest
        return f"只跟踪{canonical_topic}相关公开进展"

    def _merge_keywords(self, segments: list[dict[str, Any]]) -> list[str]:
        merged: list[str] = []
        for segment in segments:
            for keyword in segment.get("retrieval_keywords", []):
                if keyword not in merged:
                    merged.append(keyword)
        return merged[:8]

    def _merge_host_summaries(self, segments: list[dict[str, Any]]) -> str:
        summaries: list[str] = []
        for segment in segments:
            summary = str(segment.get("host_view_summary", "")).strip()
            if summary and summary not in summaries:
                summaries.append(summary)
        return " ".join(summaries[:2])[:180]


class OpenAICompatibleBackend:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None,
        name: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.max_sentence_analysis_items = int(os.getenv("EPISODE_DRAFT_SENTENCE_ANALYSIS_MAX_ITEMS", "120") or "120")
        self._heuristic = HeuristicBackend()

    def analyze_sentences(self, texts: list[str]) -> AnalysisBatchResult:
        if len(texts) > self.max_sentence_analysis_items:
            return self._heuristic.analyze_sentences(texts)
        prompt = build_sentence_analysis_prompt()
        payload = self._chat(prompt, json.dumps({"sentences": texts}, ensure_ascii=False))
        try:
            items = json.loads(payload).get("items", [])
            if len(items) != len(texts):
                raise RuntimeError("sentence_analysis_missing_fields:item_count_mismatch")
            analyses = [
                SentenceAnalysis(
                    sentence_type=str(item["sentence_type"]),
                    topic_hint=str(item["topic_hint"]),
                    confidence=float(item["confidence"]),
                    is_host_commentary=bool(item["is_host_commentary"]),
                )
                for item in items
            ]
        except Exception as exc:
            raise RuntimeError(f"sentence_analysis_invalid_response:{exc}") from exc

        return AnalysisBatchResult(
            items=analyses,
            model_runs=[ModelRun(stage="sentence_analysis", backend=self.name, target_id="episode")],
        )

    def summarize_segment(self, sentences: list[SentenceUnit], segment_id: str) -> StructuredResult:
        prompt = build_segment_extract_prompt()
        content = json.dumps(
            {
                "segment_id": segment_id,
                "sentences": [
                    {
                        "sentence_id": item.sentence_id,
                        "start": item.start,
                        "end": item.end,
                        "text": item.text,
                        "sentence_type": item.sentence_type,
                        "is_host_commentary": item.is_host_commentary,
                    }
                    for item in sentences
                ],
            },
            ensure_ascii=False,
        )
        try:
            data = json.loads(self._chat(prompt, content))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"segment_extract_invalid_json:{exc}") from exc
        self._require_fields(
            data,
            (
                "topic_candidate",
                "tracking_scope_candidate",
                "segment_summary",
                "retrieval_keywords",
                "host_view_summary",
                "quote_anchors",
                "angle_type",
                "subscope_label",
                "confidence",
            ),
            "segment_extract",
        )
        data["quote_anchors"] = self._parse_quote_anchors(data.get("quote_anchors", []), sentences, segment_id)
        data["confidence"] = float(data.get("confidence", 0.7))
        data["segment_id"] = segment_id
        data["start"] = sentences[0].start
        data["end"] = sentences[-1].end
        data["start_sentence_id"] = sentences[0].sentence_id
        data["end_sentence_id"] = sentences[-1].sentence_id
        data["sentence_ids"] = [item.sentence_id for item in sentences]
        data["segment_role"] = self._normalize_segment_role(data.get("segment_role"), sentences, data.get("angle_type"))
        data["review_status"] = "ready" if data["confidence"] >= 0.72 and data["quote_anchors"] else "needs_review"
        if data.get("angle_type") not in ANGLE_TYPES:
            data["angle_type"] = "fact_update"
        return StructuredResult(
            data=data,
            model_runs=[ModelRun(stage="segment_extract", backend=self.name, target_id=segment_id, confidence=data["confidence"])],
        )

    def merge_topics(self, segments: list[dict[str, Any]]) -> StructuredResult:
        prompt = build_topic_merge_prompt()
        content = json.dumps({"segments": self._json_ready(segments)}, ensure_ascii=False)
        try:
            data = json.loads(self._chat(prompt, content))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"topic_merge_invalid_json:{exc}") from exc
        self._require_fields(data, ("topics",), "topic_merge")
        topics = data.get("topics", [])
        for index, topic in enumerate(topics, start=1):
            topic.setdefault("topic_id", f"topic_{index:02d}")
            topic["retrieval_keywords"] = [str(item) for item in topic.get("retrieval_keywords", [])]
            topic["segment_ids"] = [str(item) for item in topic.get("segment_ids", [])]
            topic["confidence"] = float(topic.get("confidence", 0.7))
            self._require_fields(
                topic,
                (
                    "canonical_topic",
                    "tracking_scope",
                    "retrieval_keywords",
                    "host_overall_view_summary",
                    "segment_ids",
                    "review_status",
                    "confidence",
                ),
                "topic_merge",
            )
            if topic.get("review_status") not in {"ready", "needs_review"}:
                topic["review_status"] = "needs_review"
        return StructuredResult(
            data={"topics": topics},
            model_runs=[ModelRun(stage="topic_merge", backend=self.name, target_id="episode")],
        )

    def _parse_quote_anchors(
        self,
        items: list[dict[str, Any]],
        sentences: list[SentenceUnit],
        segment_id: str,
    ) -> list[QuoteAnchor]:
        by_sentence_id = {item.sentence_id: item for item in sentences}
        anchors: list[QuoteAnchor] = []
        for index, item in enumerate(items, start=1):
            sentence_id = str(item.get("sentence_id", ""))
            source_sentence = by_sentence_id.get(sentence_id)
            if source_sentence is None:
                continue
            text = str(item.get("text") or source_sentence.text)
            anchors.append(
                QuoteAnchor(
                    quote_id=f"{segment_id}_quote_{index:02d}",
                    sentence_id=sentence_id,
                    start=float(item.get("start", source_sentence.start)),
                    end=float(item.get("end", source_sentence.end)),
                    text=text,
                    confidence=float(item.get("confidence", 0.7)),
                    reason=str(item.get("reason", "model_selected_quote")),
                )
            )
        return anchors[:2]

    def _chat(self, system_prompt: str, user_content: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

    def _normalize_segment_role(self, value: Any, sentences: list[SentenceUnit], angle_type: Any) -> str:
        segment_role = str(value or "").strip()
        normalized_angle = str(angle_type) if angle_type in ANGLE_TYPES else "fact_update"
        inferred_role = self._heuristic._infer_segment_role(sentences, normalized_angle)
        if segment_role in SEGMENT_ROLES:
            if segment_role == "supporting_context" and inferred_role in {"core_argument", "proposal"}:
                text = "".join(item.text for item in sentences)
                if not any(marker in text for marker in ANECDOTE_MARKERS):
                    return inferred_role
            return segment_role
        return inferred_role

    def _require_fields(self, data: dict[str, Any], required: tuple[str, ...], stage: str) -> None:
        missing = [field for field in required if field not in data]
        if missing:
            raise RuntimeError(f"{stage}_missing_fields:{','.join(missing)}")

    def _json_ready(self, value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return {key: self._json_ready(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_ready(item) for item in value]
        return value


class HybridBackend:
    name = "hybrid"

    def __init__(
        self,
        local_backend: AnalysisBackend | None,
        remote_backend: AnalysisBackend | None,
        fallback_backend: AnalysisBackend | None = None,
    ) -> None:
        self.local_backend = local_backend
        self.remote_backend = remote_backend
        self.fallback_backend = fallback_backend or HeuristicBackend()
        self._disabled_local_stages: dict[str, str] = {}

    def analyze_sentences(self, texts: list[str]) -> AnalysisBatchResult:
        return self.fallback_backend.analyze_sentences(texts)

    def summarize_segment(self, sentences: list[SentenceUnit], segment_id: str) -> StructuredResult:
        local_result, local_failure = self._attempt_structured(
            self.local_backend,
            "segment_extract",
            segment_id,
            lambda backend: backend.summarize_segment(sentences, segment_id),
        )
        remote_failure: ModelRun | None = None
        if local_result is not None and not self._segment_needs_remote(local_result.data):
            if local_failure is not None:
                local_result.model_runs.append(local_failure)
            return local_result

        if self.remote_backend is not None:
            remote_result, remote_failure = self._attempt_structured(
                self.remote_backend,
                "segment_extract",
                segment_id,
                lambda backend: backend.summarize_segment(sentences, segment_id),
            )
            if remote_result is not None:
                if local_result is None:
                    if local_failure is not None:
                        remote_result.model_runs.insert(0, local_failure)
                    if remote_failure is not None:
                        remote_result.model_runs.append(remote_failure)
                    return remote_result
                if remote_result.data.get("confidence", 0.0) >= local_result.data.get("confidence", 0.0):
                    remote_result.model_runs = local_result.model_runs + remote_result.model_runs
                    if local_failure is not None:
                        remote_result.model_runs.append(local_failure)
                    if remote_failure is not None:
                        remote_result.model_runs.append(remote_failure)
                    return remote_result
                local_result.model_runs.extend(remote_result.model_runs)
                if local_failure is not None:
                    local_result.model_runs.append(local_failure)
                if remote_failure is not None:
                    local_result.model_runs.append(remote_failure)
                return local_result
            if local_result is not None and local_failure is not None:
                local_result.model_runs.append(local_failure)

        fallback_result = local_result or self.fallback_backend.summarize_segment(sentences, segment_id)
        if local_failure is not None:
            fallback_result.model_runs.append(local_failure)
        if remote_failure is not None:
            fallback_result.model_runs.append(remote_failure)
        return fallback_result

    def merge_topics(self, segments: list[dict[str, Any]]) -> StructuredResult:
        local_result, local_failure = self._attempt_structured(
            self.local_backend,
            "topic_merge",
            "episode",
            lambda backend: backend.merge_topics(segments),
        )
        remote_failure: ModelRun | None = None
        if local_result is not None and not self._topics_need_remote(local_result.data):
            if local_failure is not None:
                local_result.model_runs.append(local_failure)
            return local_result

        if self.remote_backend is not None:
            remote_result, remote_failure = self._attempt_structured(
                self.remote_backend,
                "topic_merge",
                "episode",
                lambda backend: backend.merge_topics(segments),
            )
            if remote_result is not None:
                if local_result is None:
                    if local_failure is not None:
                        remote_result.model_runs.insert(0, local_failure)
                    if remote_failure is not None:
                        remote_result.model_runs.append(remote_failure)
                    return remote_result
                remote_result.model_runs = local_result.model_runs + remote_result.model_runs
                if local_failure is not None:
                    remote_result.model_runs.append(local_failure)
                if remote_failure is not None:
                    remote_result.model_runs.append(remote_failure)
                return remote_result

        fallback_result = local_result or self.fallback_backend.merge_topics(segments)
        if local_failure is not None:
            fallback_result.model_runs.append(local_failure)
        if remote_failure is not None:
            fallback_result.model_runs.append(remote_failure)
        return fallback_result

    def _attempt_structured(self, backend: AnalysisBackend | None, stage: str, target_id: str, action):
        if backend is None:
            return None, None
        if backend is self.local_backend and stage in self._disabled_local_stages:
            return None, ModelRun(
                stage=stage,
                backend=backend.name,
                target_id=target_id,
                status="failed",
                reason=self._disabled_local_stages[stage],
            )
        try:
            return action(backend), None
        except Exception as exc:
            reason = self._classify_error(exc)
            if backend is self.local_backend and reason in {"timeout", "backend_error"}:
                self._disabled_local_stages[stage] = reason
            return None, ModelRun(stage=stage, backend=backend.name, target_id=target_id, status="failed", reason=reason)

    def _attempt_batch(self, backend: AnalysisBackend | None, stage: str, target_id: str, action):
        if backend is None:
            return None, None
        if backend is self.local_backend and stage in self._disabled_local_stages:
            return None, ModelRun(
                stage=stage,
                backend=backend.name,
                target_id=target_id,
                status="failed",
                reason=self._disabled_local_stages[stage],
            )
        try:
            return action(backend), None
        except Exception as exc:
            reason = self._classify_error(exc)
            if backend is self.local_backend and reason in {"timeout", "backend_error"}:
                self._disabled_local_stages[stage] = reason
            return None, ModelRun(stage=stage, backend=backend.name, target_id=target_id, status="failed", reason=reason)

    def _classify_error(self, exc: Exception) -> str:
        message = str(exc).lower()
        if isinstance(exc, requests.Timeout) or "timed out" in message or "readtimeout" in message:
            return "timeout"
        if "invalid_json" in message or "invalid_response" in message or isinstance(exc, json.JSONDecodeError):
            return "invalid_json"
        if "missing_fields" in message:
            return "missing_fields"
        return "backend_error"

    def _segment_needs_remote(self, data: dict[str, Any]) -> bool:
        return (
            float(data.get("confidence", 0.0)) < 0.72
            or not data.get("quote_anchors")
            or data.get("angle_type") not in ANGLE_TYPES
            or not data.get("retrieval_keywords")
        )

    def _topics_need_remote(self, data: dict[str, Any]) -> bool:
        topics = data.get("topics", [])
        if not topics:
            return True
        if any(topic.get("review_status") == "needs_review" for topic in topics):
            return True
        return any(float(topic.get("confidence", 0.0)) < 0.72 for topic in topics)


def get_backend(mode: str = "auto") -> AnalysisBackend:
    load_project_env()
    heuristic = HeuristicBackend()
    local_backend = None
    remote_backend = None
    local_timeout = _read_timeout("EPISODE_DRAFT_LOCAL_TIMEOUT_SECONDS", 180.0)
    remote_timeout = _read_timeout("EPISODE_DRAFT_API_TIMEOUT_SECONDS", 60.0)

    local_base_url = os.getenv("EPISODE_DRAFT_LOCAL_API_BASE")
    local_model = os.getenv("EPISODE_DRAFT_LOCAL_MODEL")
    local_api_key = os.getenv("EPISODE_DRAFT_LOCAL_API_KEY")
    if local_base_url and local_model:
        local_backend = OpenAICompatibleBackend(local_base_url, local_model, local_api_key, "local_api", local_timeout)

    remote_base_url = os.getenv("EPISODE_DRAFT_API_BASE")
    remote_model = os.getenv("EPISODE_DRAFT_API_MODEL")
    remote_api_key = os.getenv("EPISODE_DRAFT_API_KEY")
    if remote_base_url and remote_model:
        remote_backend = OpenAICompatibleBackend(remote_base_url, remote_model, remote_api_key, "remote_api", remote_timeout)

    if mode == "heuristic":
        return heuristic
    if mode == "local":
        if local_backend is None:
            raise RuntimeError("local_backend_not_configured")
        return local_backend
    if mode == "api":
        if remote_backend is None:
            raise RuntimeError("api_backend_not_configured")
        return remote_backend
    if mode == "auto":
        if local_backend is not None or remote_backend is not None:
            return HybridBackend(local_backend, remote_backend, heuristic)
        return heuristic
    return heuristic


def _read_timeout(env_name: str, default: float) -> float:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return default
    try:
        return max(float(raw), 1.0)
    except ValueError:
        return default
