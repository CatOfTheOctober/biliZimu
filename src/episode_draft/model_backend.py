"""Backend abstraction for sentence and block analysis."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

import requests

from .models import HostQuoteCandidate, SentenceUnit


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


@dataclass
class SentenceAnalysis:
    sentence_type: str
    topic_hint: str
    confidence: float
    is_host_commentary: bool


class AnalysisBackend(Protocol):
    name: str

    def analyze_sentences(self, texts: list[str]) -> list[SentenceAnalysis]:
        ...

    def summarize_block(self, sentences: list[SentenceUnit], block_id: str) -> dict[str, object]:
        ...


class HeuristicBackend:
    name = "heuristic"

    def analyze_sentences(self, texts: list[str]) -> list[SentenceAnalysis]:
        return [self._analyze_sentence(text) for text in texts]

    def summarize_block(self, sentences: list[SentenceUnit], block_id: str) -> dict[str, object]:
        factual = [item for item in sentences if item.sentence_type == "news_fact"]
        commentary = [item for item in sentences if item.is_host_commentary]
        primary = factual[0] if factual else sentences[0]
        title_candidate = self._make_title(primary.text)
        background_lines = [item.text for item in (factual[:3] or sentences[:3])]
        view_lines = [item.text for item in (commentary[:2] or sentences[:2])]

        quote_candidates = [
            HostQuoteCandidate(
                quote_id=f"{block_id}_quote_{idx:02d}",
                start=item.start,
                end=item.end,
                text=item.text,
                confidence=item.confidence,
                reason="commentary_sentence",
            )
            for idx, item in enumerate(commentary[:3], start=1)
        ]

        return {
            "title_candidate": title_candidate,
            "direct_scope_candidate": f"围绕“{title_candidate}”在原节目中的直接讨论整理，不扩展到更大议题。",
            "background_summary": " ".join(background_lines),
            "host_view_summary_candidate": " ".join(view_lines),
            "host_quote_candidates": quote_candidates,
            "confidence": round(
                sum(item.confidence for item in sentences) / max(len(sentences), 1),
                3,
            ),
        }

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
        compact = text.replace("，", " ").replace("。", " ").replace("：", " ")
        compact = compact.replace("、", " ").replace(",", " ").replace("?", " ")
        parts = [item.strip() for item in compact.split() if item.strip()]
        if not parts:
            return text[:16]

        candidates = []
        for part in parts:
            item = part[:18]
            if len(item) < 2 or item in STOP_PHRASES:
                continue
            candidates.append(item)
        return candidates[0] if candidates else text[:16]

    def _make_title(self, text: str) -> str:
        stripped = text.strip("，。！？；：,.!?;: ")
        if len(stripped) <= 20:
            return stripped
        return stripped[:20].rstrip("，。！？；：,.!?;: ")


class OpenAICompatibleBackend:
    def __init__(self, base_url: str, model: str, api_key: str | None, name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.name = name

    def analyze_sentences(self, texts: list[str]) -> list[SentenceAnalysis]:
        prompt = (
            "你是中文时政视频整理助手。"
            "请把每句话标为 news_fact、host_commentary、transition、noise 之一，"
            "并给出 topic_hint、confidence、is_host_commentary。"
            "只返回 JSON 数组。"
        )
        payload = self._chat(prompt, json.dumps(texts, ensure_ascii=False))
        try:
            items = json.loads(payload)
            if isinstance(items, dict):
                items = items.get("items", [])
            return [
                SentenceAnalysis(
                    sentence_type=item["sentence_type"],
                    topic_hint=item["topic_hint"],
                    confidence=float(item["confidence"]),
                    is_host_commentary=bool(item["is_host_commentary"]),
                )
                for item in items
            ]
        except Exception as exc:
            raise RuntimeError(f"sentence_analysis_invalid_response:{exc}") from exc

    def summarize_block(self, sentences: list[SentenceUnit], block_id: str) -> dict[str, object]:
        prompt = (
            "你是中文时政视频整理助手。"
            "请基于一个新闻块的句子生成 JSON，包含 title_candidate、"
            "direct_scope_candidate、background_summary、host_view_summary_candidate、"
            "host_quote_candidates、confidence。"
        )
        content = json.dumps(
            [
                {
                    "start": item.start,
                    "end": item.end,
                    "text": item.text,
                    "sentence_type": item.sentence_type,
                    "is_host_commentary": item.is_host_commentary,
                }
                for item in sentences
            ],
            ensure_ascii=False,
        )
        payload = self._chat(prompt, content)
        data = json.loads(payload)
        quotes = [
            HostQuoteCandidate(
                quote_id=f"{block_id}_quote_{idx:02d}",
                start=float(item["start"]),
                end=float(item["end"]),
                text=item["text"],
                confidence=float(item.get("confidence", 0.7)),
                reason=item.get("reason", "model_generated"),
            )
            for idx, item in enumerate(data.get("host_quote_candidates", []), start=1)
        ]
        data["host_quote_candidates"] = quotes
        return data

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
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]


def get_backend(mode: str = "auto") -> AnalysisBackend:
    if mode == "heuristic":
        return HeuristicBackend()

    if mode in {"auto", "local"}:
        base_url = os.getenv("EPISODE_DRAFT_LOCAL_API_BASE")
        model = os.getenv("EPISODE_DRAFT_LOCAL_MODEL")
        api_key = os.getenv("EPISODE_DRAFT_LOCAL_API_KEY")
        if base_url and model:
            return OpenAICompatibleBackend(base_url, model, api_key, "local_api")
        if mode == "local":
            raise RuntimeError("local_backend_not_configured")

    if mode in {"auto", "api"}:
        base_url = os.getenv("EPISODE_DRAFT_API_BASE")
        model = os.getenv("EPISODE_DRAFT_API_MODEL")
        api_key = os.getenv("EPISODE_DRAFT_API_KEY")
        if base_url and model:
            return OpenAICompatibleBackend(base_url, model, api_key, "remote_api")
        if mode == "api":
            raise RuntimeError("api_backend_not_configured")

    return HeuristicBackend()
