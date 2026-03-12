import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from shuiqian_review.models import EpisodePackage


def build_package(source_url: str = "https://www.news.cn/item") -> EpisodePackage:
    return EpisodePackage.from_dict(
        {
            "project_title": "test",
            "source_policy": "official_first_mainstream_media_only",
            "episode": {
                "title": "episode",
                "air_date": "2019-11-07",
                "source_url": "https://www.bilibili.com/video/BV1",
                "transcript_status": "platform_subtitle",
                "transcript_excerpt": "excerpt",
                "news_summary": "summary",
                "recording_cutoff_date": "2026-03-12",
                "segments": [
                    {
                        "title": "seg",
                        "start": "00:00:00",
                        "end": "00:01:00",
                        "summary": "seg summary"
                    }
                ]
            },
            "news_items": [
                {
                    "title": "news",
                    "direct_scope": "scope",
                    "original_background": "background",
                    "host_quote": "quote",
                    "host_view_summary": "summary",
                    "current_status": "status",
                    "evidence_status": "sufficient",
                    "allowed_sources_used": ["新华社"],
                    "timeline": [
                        {
                            "date": "2020-01-01",
                            "event": "event",
                            "source": {
                                "source_name": "新华社",
                                "source_type": "mainstream_media",
                                "source_url": source_url,
                                "source_label": "新华社 2020-01-01",
                                "published_date": "2020-01-01"
                            },
                            "relation_to_host_view": "relation",
                            "relevance_note": "direct",
                            "verified": True
                        }
                    ],
                    "clip_candidates": []
                }
            ]
        }
    )


class ValidationTests(unittest.TestCase):
    def test_whitelisted_mainstream_source_passes(self) -> None:
        package = build_package()
        issues = package.validate()
        errors = [item for item in issues if item.level == "error"]
        self.assertEqual(errors, [])

    def test_disallowed_social_source_fails(self) -> None:
        package = build_package("https://weibo.com/item")
        issues = package.validate()
        messages = [item.message for item in issues]
        self.assertTrue(any(message.startswith("source_not_allowed") for message in messages))

    def test_missing_host_quote_fails(self) -> None:
        package = build_package()
        package.news_items[0].host_quote = ""
        issues = package.validate()
        messages = [item.message for item in issues]
        self.assertIn("host_quote_required", messages)


if __name__ == "__main__":
    unittest.main()
