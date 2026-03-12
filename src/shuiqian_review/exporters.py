"""Markdown exporters for production-ready episode packages."""

from __future__ import annotations

import re
from pathlib import Path

from .models import EpisodePackage, NewsCard


def slugify(text: str) -> str:
    ascii_like = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip().lower())
    ascii_like = re.sub(r"-{2,}", "-", ascii_like).strip("-")
    return ascii_like or "news"


def export_package(package: EpisodePackage, output_dir: str | Path) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    generated = [
        _write_text(out / "episode_overview.md", build_episode_overview(package)),
        _write_text(out / "production_pack.md", build_production_pack(package)),
        _write_text(out / "sources.md", build_sources_index(package)),
    ]

    for idx, news in enumerate(package.news_items, start=1):
        filename = f"news_{idx:02d}_{slugify(news.title)}.md"
        generated.append(_write_text(out / filename, build_news_card(news, idx)))
    return generated


def build_episode_overview(package: EpisodePackage) -> str:
    episode = package.episode
    lines = [
        f"# {package.project_title}",
        "",
        "## Episode Card",
        f"- 标题：{episode.title}",
        f"- 播出日期：{episode.air_date}",
        f"- 原节目链接：{episode.source_url}",
        f"- 字幕状态：{episode.transcript_status}",
        f"- 录制截点：{episode.recording_cutoff_date}",
        f"- 本期新闻概览：{episode.news_summary}",
        "",
        "## 节目分段",
    ]
    if episode.segments:
        for segment in episode.segments:
            lines.append(f"- {segment.start} - {segment.end}｜{segment.title}：{segment.summary}")
    else:
        lines.append("- 暂未填写")
    return "\n".join(lines) + "\n"


def build_news_card(news: NewsCard, index: int) -> str:
    lines = [
        f"# 新闻 {index:02d}：{news.title}",
        "",
        "## 背景",
        news.original_background,
        "",
        "## 原节目观点",
        f"> {news.host_quote}",
        "",
        news.host_view_summary,
        "",
        "## 后续关键节点",
    ]
    for event in news.timeline:
        lines.append(
            f"- {event.date}｜{event.event}｜来源：{event.source.source_label}｜关联：{event.relation_to_host_view}"
        )
    lines.extend(
        [
            "",
            "## 当前现状",
            news.current_status,
            "",
            "## 成片提示",
            f"- 直接主线：{news.direct_scope}",
            f"- 证据状态：{news.evidence_status}",
            "",
            "## 可引用片段",
        ]
    )
    if news.clip_candidates:
        for clip in news.clip_candidates:
            lines.append(f"- {clip.start} - {clip.end}｜{clip.usage_note}")
    else:
        lines.append("- 暂无")
    return "\n".join(lines) + "\n"


def build_production_pack(package: EpisodePackage) -> str:
    lines = [
        f"# {package.episode.title} 成片资料包",
        "",
        "## 开场",
        f"- 今天回看的是 {package.episode.air_date} 播出的《睡前消息》。",
        f"- 这一期一共涉及 {len(package.news_items)} 条新闻。",
        "",
        "## 脚本提纲",
        "- 开场：概述本期新闻与回看视角。",
    ]
    for idx, news in enumerate(package.news_items, start=1):
        lines.extend(
            [
                f"- 新闻 {idx}：{news.title}",
                f"  - 背景：{news.original_background}",
                f"  - 原节目观点：{news.host_view_summary}",
                f"  - 现状：{news.current_status}",
            ]
        )
    lines.extend(
        [
            "",
            "## 画面来源简称",
        ]
    )
    seen: set[tuple[str, str]] = set()
    for news in package.news_items:
        for event in news.timeline:
            key = (event.source.source_label, event.source.source_url)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {event.source.source_label}｜{event.source.source_url}")
    return "\n".join(lines) + "\n"


def build_sources_index(package: EpisodePackage) -> str:
    lines = [
        f"# {package.episode.title} 来源清单",
        "",
    ]
    for idx, news in enumerate(package.news_items, start=1):
        lines.append(f"## 新闻 {idx}：{news.title}")
        for event in news.timeline:
            src = event.source
            lines.append(
                f"- {event.date}｜{src.source_name}｜{src.source_label}｜{src.published_date}｜{src.source_url}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_text(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path
