import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from shuiqian_review.exporters import export_package
from shuiqian_review.io_utils import load_package


class ExportTests(unittest.TestCase):
    def test_export_generates_expected_files(self) -> None:
        package = load_package(ROOT / "samples" / "episode_2019-11-07.sample.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            generated = export_package(package, tmpdir)
            names = sorted(path.name for path in generated)
            self.assertEqual(
                names,
                [
                    "episode_overview.md",
                    "news_01_样例新闻-地方国资平台风险处置.md",
                    "news_02_样例新闻-教育政策执行观察.md",
                    "production_pack.md",
                    "sources.md",
                ],
            )


if __name__ == "__main__":
    unittest.main()
