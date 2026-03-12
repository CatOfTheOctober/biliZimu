import json
import os
import requests
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from episode_draft.draft_generator import generate_draft
from episode_draft.doctor import format_doctor_report, run_doctor
from episode_draft.model_backend import HeuristicBackend, HybridBackend, get_backend
from episode_draft.prompts import build_segment_extract_prompt, build_sentence_analysis_prompt, build_topic_merge_prompt


def build_bundle(root: Path, track_segments: Optional[List[dict]] = None) -> Path:
    bundle_dir = root / "2026-03-03_demo_BVTEST"
    (bundle_dir / "derived").mkdir(parents=True)
    (bundle_dir / "raw").mkdir(parents=True)
    (bundle_dir / "manifest").mkdir(parents=True)

    default_segments = [
        {"start_time": 0.0, "end_time": 2.0, "text": "今天先说柳州城投债。", "confidence": 1.0, "source": "asr"},
        {"start_time": 2.0, "end_time": 4.0, "text": "柳州城投去年融资压力很大。", "confidence": 1.0, "source": "asr"},
        {"start_time": 4.0, "end_time": 7.0, "text": "我认为这个问题不是短期流动性，而是地方基建模式失衡。", "confidence": 1.0, "source": "asr"},
        {"start_time": 7.0, "end_time": 8.0, "text": "接下来聊小学教育。", "confidence": 1.0, "source": "asr"},
        {"start_time": 8.0, "end_time": 10.0, "text": "某地小学午休政策引发争议。", "confidence": 1.0, "source": "asr"},
        {"start_time": 10.0, "end_time": 12.5, "text": "我觉得学校和家长的责任边界没有说清楚。", "confidence": 1.0, "source": "asr"},
    ]

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
                "segments": track_segments or default_segments,
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


def env_with_pythonpath() -> dict:
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SRC) if not current else f"{SRC};{current}"
    return env


class EpisodeDraftTests(unittest.TestCase):
    @mock.patch("episode_draft.doctor.requests.get")
    def test_doctor_reports_local_and_remote_status(self, mock_get) -> None:
        env_path = ROOT / ".env"
        original_env_text = env_path.read_text(encoding="utf-8") if env_path.exists() else None
        original_values = {
            "MODELSCOPE_CACHE": os.environ.get("MODELSCOPE_CACHE"),
            "OLLAMA_MODELS": os.environ.get("OLLAMA_MODELS"),
            "EPISODE_DRAFT_LOCAL_API_BASE": os.environ.get("EPISODE_DRAFT_LOCAL_API_BASE"),
            "EPISODE_DRAFT_LOCAL_MODEL": os.environ.get("EPISODE_DRAFT_LOCAL_MODEL"),
            "EPISODE_DRAFT_API_BASE": os.environ.get("EPISODE_DRAFT_API_BASE"),
            "EPISODE_DRAFT_API_MODEL": os.environ.get("EPISODE_DRAFT_API_MODEL"),
            "EPISODE_DRAFT_API_KEY": os.environ.get("EPISODE_DRAFT_API_KEY"),
        }

        for key in original_values:
            os.environ.pop(key, None)

        env_path.write_text(
            "\n".join(
                [
                    "MODELSCOPE_CACHE=D:\\Model\\Funasr_model\\modelscope_cache",
                    "OLLAMA_MODELS=D:\\Model\\ollama",
                    "EPISODE_DRAFT_LOCAL_API_BASE=http://127.0.0.1:11434/v1",
                    "EPISODE_DRAFT_LOCAL_MODEL=qwen2.5:3b",
                    "EPISODE_DRAFT_API_BASE=https://api.deepseek.com/v1",
                    "EPISODE_DRAFT_API_MODEL=deepseek-chat",
                    "EPISODE_DRAFT_API_KEY=test-key",
                ]
            ),
            encoding="utf-8",
        )

        local_response = mock.Mock()
        local_response.ok = True
        local_response.status_code = 200
        remote_response = mock.Mock()
        remote_response.ok = True
        remote_response.status_code = 200
        mock_get.side_effect = [local_response, remote_response]

        try:
            report = run_doctor()
            rendered = format_doctor_report(report)
        finally:
            if original_env_text is None:
                if env_path.exists():
                    env_path.unlink()
            else:
                env_path.write_text(original_env_text, encoding="utf-8")

            for key, value in original_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertTrue(report["env"]["env_file_found"])
        self.assertTrue(report["local"]["ready"])
        self.assertTrue(report["remote"]["ready"])
        self.assertTrue(report["local"]["connectivity"]["ok"])
        self.assertTrue(report["remote"]["connectivity"]["ok"])
        self.assertIn("episode_draft doctor", rendered)
        self.assertIn("Local model:", rendered)
        self.assertIn("Remote model:", rendered)

    def test_prompt_templates_include_key_constraints(self) -> None:
        sentence_prompt = build_sentence_analysis_prompt()
        segment_prompt = build_segment_extract_prompt()
        topic_prompt = build_topic_merge_prompt()

        self.assertIn("news_fact", sentence_prompt)
        self.assertIn("host_commentary", sentence_prompt)
        self.assertIn("topic_hint", sentence_prompt)

        self.assertIn("不允许补充外部事实或背景", segment_prompt)
        self.assertIn("retrieval_keywords 是后续检索标签", segment_prompt)
        self.assertIn("quote_anchors 必须引用输入里的原句", segment_prompt)
        self.assertIn("background、fact_update、host_judgment", segment_prompt)
        self.assertIn("segment_role", segment_prompt)
        self.assertIn("supporting_context", segment_prompt)

        self.assertIn("后续跟踪边界相同", topic_prompt)
        self.assertIn("地方个案、责任主体、全国扩展", topic_prompt)
        self.assertIn("主视图是主题视图", topic_prompt)
        self.assertIn("1 到 3 个真正可跟踪的主主题", topic_prompt)

    def test_get_backend_loads_project_env(self) -> None:
        env_path = ROOT / ".env"
        original_env_text = env_path.read_text(encoding="utf-8") if env_path.exists() else None
        original_values = {
            "MODELSCOPE_CACHE": os.environ.get("MODELSCOPE_CACHE"),
            "EPISODE_DRAFT_LOCAL_API_BASE": os.environ.get("EPISODE_DRAFT_LOCAL_API_BASE"),
            "EPISODE_DRAFT_LOCAL_MODEL": os.environ.get("EPISODE_DRAFT_LOCAL_MODEL"),
            "EPISODE_DRAFT_API_BASE": os.environ.get("EPISODE_DRAFT_API_BASE"),
            "EPISODE_DRAFT_API_MODEL": os.environ.get("EPISODE_DRAFT_API_MODEL"),
        }

        os.environ["MODELSCOPE_CACHE"] = "D:\\legacy\\modelscope_cache"
        for key in original_values:
            if key != "MODELSCOPE_CACHE":
                os.environ.pop(key, None)

        env_path.write_text(
            "\n".join(
                [
                    "MODELSCOPE_CACHE=D:\\Model\\Funasr_model\\modelscope_cache",
                    "EPISODE_DRAFT_LOCAL_API_BASE=http://127.0.0.1:11434/v1",
                    "EPISODE_DRAFT_LOCAL_MODEL=qwen2.5:3b",
                    "EPISODE_DRAFT_LOCAL_TIMEOUT_SECONDS=321",
                    "EPISODE_DRAFT_API_BASE=https://api.deepseek.com/v1",
                    "EPISODE_DRAFT_API_MODEL=deepseek-chat",
                    "EPISODE_DRAFT_API_TIMEOUT_SECONDS=45",
                ]
            ),
            encoding="utf-8",
        )

        try:
            backend = get_backend("auto")
            self.assertEqual(backend.name, "hybrid")
            self.assertEqual(os.environ["MODELSCOPE_CACHE"], "D:\\Model\\Funasr_model\\modelscope_cache")
            self.assertEqual(backend.local_backend.timeout_seconds, 321.0)
            self.assertEqual(backend.remote_backend.timeout_seconds, 45.0)
        finally:
            if original_env_text is None:
                if env_path.exists():
                    env_path.unlink()
            else:
                env_path.write_text(original_env_text, encoding="utf-8")

            for key, value in original_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_generate_draft_outputs_topics_with_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = build_bundle(Path(tmpdir))
            draft = generate_draft(str(bundle_dir), backend_mode="heuristic")

        self.assertEqual(draft.source_bundle_id, "bundle_demo")
        self.assertEqual(draft.selected_track["segment_count"], 6)
        self.assertGreaterEqual(len(draft.news_topics), 2)
        self.assertTrue(all(topic.segments for topic in draft.news_topics))
        self.assertTrue(any(segment.quote_anchors for topic in draft.news_topics for segment in topic.segments))
        self.assertTrue(all(segment.sentence_ids for topic in draft.news_topics for segment in topic.segments))
        self.assertTrue(all(topic.canonical_topic for topic in draft.news_topics))
        self.assertTrue(all(segment.segment_role for topic in draft.news_topics for segment in topic.segments))

    def test_generate_draft_merges_same_topic_across_multiple_segments(self) -> None:
        segments = [
            {"start_time": 0.0, "end_time": 2.0, "text": "今天先说柳州城投债。", "confidence": 1.0, "source": "asr"},
            {"start_time": 2.0, "end_time": 4.0, "text": "柳州城投去年融资压力很大。", "confidence": 1.0, "source": "asr"},
            {"start_time": 4.0, "end_time": 6.0, "text": "我觉得柳州化债节奏不能只看短期周转。", "confidence": 1.0, "source": "asr"},
            {"start_time": 6.0, "end_time": 7.0, "text": "接下来聊小学教育。", "confidence": 1.0, "source": "asr"},
            {"start_time": 7.0, "end_time": 9.0, "text": "某地小学午休政策引发争议。", "confidence": 1.0, "source": "asr"},
            {"start_time": 9.0, "end_time": 11.0, "text": "我觉得学校和家长的责任边界没有说清楚。", "confidence": 1.0, "source": "asr"},
            {"start_time": 11.0, "end_time": 12.0, "text": "再说回柳州城投债。", "confidence": 1.0, "source": "asr"},
            {"start_time": 12.0, "end_time": 14.0, "text": "柳州城投的化债安排后来还在推进。", "confidence": 1.0, "source": "asr"},
            {"start_time": 14.0, "end_time": 16.0, "text": "我认为这个风险还没有真正解除。", "confidence": 1.0, "source": "asr"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = build_bundle(Path(tmpdir), track_segments=segments)
            draft = generate_draft(str(bundle_dir), backend_mode="heuristic")

        multi_segment_topics = [topic for topic in draft.news_topics if len(topic.segments) >= 2]
        self.assertTrue(multi_segment_topics)
        self.assertTrue(
            any(
                "柳州城投" in topic.canonical_topic or any("柳州城投" in keyword for keyword in topic.retrieval_keywords)
                for topic in multi_segment_topics
            )
        )
        self.assertTrue(
            all(
                anchor.sentence_id.startswith("s")
                for topic in draft.news_topics
                for segment in topic.segments
                for anchor in segment.quote_anchors
            )
        )

    def test_generate_draft_downgrades_anecdote_to_supporting_context(self) -> None:
        segments = [
            {"start_time": 0.0, "end_time": 2.0, "text": "今天先说圣家堂封顶。", "confidence": 1.0, "source": "asr"},
            {"start_time": 2.0, "end_time": 4.0, "text": "我认为这更像持续施工的营销节点。", "confidence": 1.0, "source": "asr"},
            {"start_time": 4.0, "end_time": 6.0, "text": "现在我回忆九二年巴塞罗那奥运会的宣传片。", "confidence": 1.0, "source": "asr"},
            {"start_time": 6.0, "end_time": 8.0, "text": "当时我第一次注意到西班牙的桥梁和圣家堂。", "confidence": 1.0, "source": "asr"},
            {"start_time": 8.0, "end_time": 10.0, "text": "这些宣传都在帮助圣家堂成为国家形象广告。", "confidence": 1.0, "source": "asr"},
            {"start_time": 10.0, "end_time": 12.0, "text": "最后中国能不能借鉴这种长期文旅运营方式。", "confidence": 1.0, "source": "asr"},
            {"start_time": 12.0, "end_time": 14.0, "text": "我建议把大学作为更适合的世俗替代方案。", "confidence": 1.0, "source": "asr"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = build_bundle(Path(tmpdir), track_segments=segments)
            draft = generate_draft(str(bundle_dir), backend_mode="heuristic")

        self.assertLessEqual(len(draft.news_topics), 3)
        self.assertFalse(any("回忆" in topic.canonical_topic or "印象" in topic.canonical_topic for topic in draft.news_topics))
        supporting_segments = [
            segment
            for topic in draft.news_topics
            for segment in topic.segments
            if segment.segment_role == "supporting_context"
        ]
        self.assertTrue(supporting_segments)
        self.assertTrue(any(segment.segment_role == "supporting_context" for segment in supporting_segments))

    def test_hybrid_backend_records_timeout_reason(self) -> None:
        class TimeoutBackend:
            name = "local_api"

            def analyze_sentences(self, texts):
                raise NotImplementedError

            def summarize_segment(self, sentences, segment_id):
                raise requests.Timeout("timed out")

            def merge_topics(self, segments):
                raise NotImplementedError

        hybrid = HybridBackend(TimeoutBackend(), HeuristicBackend(), HeuristicBackend())
        sentences = [
            mock.Mock(
                sentence_id="s001",
                start=0.0,
                end=2.0,
                text="今天先说柳州城投债。",
                sentence_type="news_fact",
                is_host_commentary=False,
                confidence=0.8,
            ),
            mock.Mock(
                sentence_id="s002",
                start=2.0,
                end=4.0,
                text="我认为这个问题不是短期流动性。",
                sentence_type="host_commentary",
                is_host_commentary=True,
                confidence=0.8,
            ),
        ]

        result = hybrid.summarize_segment(sentences, "segment_01")
        failure_runs = [run for run in result.model_runs if run.backend == "local_api" and run.status == "failed"]
        self.assertTrue(failure_runs)
        self.assertEqual(failure_runs[0].reason, "timeout")

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
            payload = json.loads(draft_path.read_text(encoding="utf-8"))
            self.assertIn("news_topics", payload)
            self.assertNotIn("news_blocks", payload)

    def test_module_cli_doctor_outputs_json(self) -> None:
        env_path = ROOT / ".env"
        original_env_text = env_path.read_text(encoding="utf-8") if env_path.exists() else None
        cli_env = env_with_pythonpath()
        for key in [
            "EPISODE_DRAFT_LOCAL_API_BASE",
            "EPISODE_DRAFT_LOCAL_MODEL",
            "EPISODE_DRAFT_API_BASE",
            "EPISODE_DRAFT_API_MODEL",
            "EPISODE_DRAFT_API_KEY",
        ]:
            cli_env.pop(key, None)

        try:
            if env_path.exists():
                env_path.unlink()
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "episode_draft",
                    "doctor",
                    "--json",
                ],
                cwd=str(ROOT),
                env=cli_env,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            if original_env_text is None:
                if env_path.exists():
                    env_path.unlink()
            else:
                env_path.write_text(original_env_text, encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("local", payload)
        self.assertIn("remote", payload)


if __name__ == "__main__":
    unittest.main()
