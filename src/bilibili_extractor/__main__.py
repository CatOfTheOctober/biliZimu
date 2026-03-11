"""Compatibility shell entry for bilibili-extractor.

The legacy CLI workflow has been deprecated.
Use the project root script `下载字幕.py` as the only supported entry.
"""

import sys


DEPRECATED_MESSAGE = (
    "\n"
    "============================================================\n"
    "bilibili_extractor CLI 已废弃，仅保留兼容壳入口。\n"
    "请使用项目根目录脚本执行下载：\n"
    "  python 下载字幕.py\n"
    "============================================================\n"
)


def main() -> int:
    """Print migration guidance and exit."""
    print(DEPRECATED_MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
