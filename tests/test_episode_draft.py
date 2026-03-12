import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from episode_draft.draft_generator import generate_draft


def build_bundle(root: Path) -> Path:
    bundle_dir = root / "2026-03-03_demo_BVTEST"
    (bundle_dir / "derived").mkdir(parents=True)
    (bundle_dir / "raw").mkdir(parents=True)
    (bundle_dir / "manifest").mkdir(parents=True)

    transcript = {
        "schema_version": "1.0",
        "video": {
            "bvid": "BVTEST",
            "title": "测试节目",
            "description": "测试描述",
            "published_at": "2026-03-03T09:03:53Z",
            "uploader": "测试UP",
            "url": "https://www.bilibili.com/video/BVTEST",
            "cid": 1,
            "cover_url": "",
            "duration": 120,
            "page": 1,
            "pages": [],
        },
        "tracks": [
            {
                "track_id": "selected_asr",
                "track_type": "asr",
                "source": "asr",
                "label": "ASR",
                "language": None,
                "is_ai_generated": False,
                "segments": [
                    {"start_time": 0.0, "end_time": 2.0, "text": "今天先说柳州城投债。", "confidence": 1.0, "source": "asr"},
                    {"start_time": 2.0, "end_time": 4.0, "text": "柳州城投去年融资压力很大。", "confidence": 1.0, "source": "asr"},
                    {"start_time": 4.0, "end_time": 7.0, "text": "我认为这个问题不是短期流动性，而是地方基建模式失衡。", "confidence": 1.0, "source": "asr"},
                    {"start_time": 7.0, "end_time": 8.0, "text": "接下来聊小学教育。", "confidence": 1.0, "source": "asr"},
                    {"start_time": 8.0, "end_time": 10.0, "text": "某地小学午休政策引发争议。", "confidence": 1.0, "source": "asr"},
                    {"start_time": 10.0, "end_time": 12.5, "text": "我觉得学校和家长的责任边界没有说清楚。", "confidence": 1.0, "source": "asr"},
                ],
                "metadata": {},
            }
        ],
        "selected_track": "selected_asr",
        "quality_flags": {"has_asr": True},
        "processing": {},
    }

    manifest = {
        "schema_version": "1.0",
        "bundle_id": "bundle_demo",
        "video_id": "BVTEST",
        "created_at": "2026-03-12T00:00:00Z",
        "status": "completed",
        "assets": [],
    }

    (bundle_dir / "derived" / "TranscriptBundle.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (bundle_dir / "raw" / "video_metadata.json").write_text(
        json.dumps({"title": "测试节目"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (bundle_dir / "manifest" / "AssetManifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return bundle_dir


def env_with_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SRC) if not current else f"{SRC};{current}"
    return env


class EpisodeDraftTests(unittest.TestCase):
    def test_generate_draft_groups_sentences_into_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = build_bundle(Path(tmpdir))
            draft = generate_draft(str(bundle_dir), backend_mode="heuristic")

        self.assertEqual(draft.source_bundle_id, "bundle_demo")
        self.assertEqual(draft.selected_track["segment_count"], 6)
        self.assertGreaterEqual(len(draft.news_blocks), 2)
        self.assertTrue(any(block.host_quote_candidates for block in draft.news_blocks))
        self.assertTrue(all(block.sentence_ids for block in draft.news_blocks))
        self.assertTrue(all(block.title_candidate for block in draft.news_blocks))

    def test_module_cli_writes_episode_draft_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = build_bundle(Path(tmpdir))
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "episode_draft",
                    "draft-from-bundle",
                    str(bundle_dir),
                    "--backend",
                    "heuristic",
                ],
                cwd=str(ROOT),
                env=env_with_pythonpath(),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            draft_path = bundle_dir / "review" / "EpisodeDraft.json"
            self.assertTrue(draft_path.exists())


if __name__ == "__main__":
    unittest.main()
