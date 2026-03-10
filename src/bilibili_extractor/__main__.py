"""CLI entry point for bilibili-extractor."""

import sys
import os

# Add src directory to path when running directly
if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

from bilibili_extractor.cli import main as cli_main


def main():
    """Entry point for the bilibili-extractor command."""
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
