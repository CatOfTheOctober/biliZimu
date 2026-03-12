"""Static policy and validation rules for episode review packages."""

from __future__ import annotations

from dataclasses import dataclass

TIMELINE_RECOMMENDED_MIN = 5
TIMELINE_RECOMMENDED_MAX = 10
TIMELINE_HARD_MIN = 1

SOURCE_TYPE_OFFICIAL = "official"
SOURCE_TYPE_MAINSTREAM = "mainstream_media"

ALLOWED_MAINSTREAM_MEDIA = {
    "新华社",
    "央视新闻",
    "CCTV",
    "人民日报",
    "中国新闻网",
    "财新",
}

OFFICIAL_SOURCE_HINTS = (
    ".gov.cn",
    "gov.cn",
    "moe.gov.cn",
    "stats.gov.cn",
    "ndrc.gov.cn",
    "mof.gov.cn",
    "customs.gov.cn",
    "chinacourt.org",
    "court.gov.cn",
    "csrc.gov.cn",
    "sse.com.cn",
    "szse.cn",
    "hkexnews.hk",
)

DISALLOWED_SOURCE_HINTS = (
    "weibo.com",
    "x.com",
    "twitter.com",
    "bilibili.com",
    "zhihu.com",
    "tieba.baidu.com",
    "douyin.com",
    "toutiao.com",
)

ALLOWED_EVIDENCE_STATUSES = {
    "sufficient",
    "insufficient_public_info",
}

ALLOWED_TRANSCRIPT_STATUSES = {
    "platform_subtitle",
    "manual_transcript",
    "asr_generated",
    "missing",
}


@dataclass(frozen=True)
class SourceDecision:
    allowed: bool
    reason: str


def classify_source(source_name: str, source_type: str, source_url: str) -> SourceDecision:
    name = source_name.strip()
    source_type = source_type.strip()
    url = source_url.strip().lower()

    if any(hint in url for hint in DISALLOWED_SOURCE_HINTS):
        return SourceDecision(False, "source_url_matches_disallowed_hint")

    if source_type == SOURCE_TYPE_OFFICIAL:
        if any(hint in url for hint in OFFICIAL_SOURCE_HINTS):
            return SourceDecision(True, "official_domain_match")
        return SourceDecision(False, "official_source_requires_known_official_domain")

    if source_type == SOURCE_TYPE_MAINSTREAM:
        if name in ALLOWED_MAINSTREAM_MEDIA:
            return SourceDecision(True, "mainstream_source_whitelisted")
        return SourceDecision(False, "mainstream_source_not_whitelisted")

    return SourceDecision(False, "source_type_not_allowed")
