"""CLI for TranscriptBundle -> EpisodeDraft conversion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .doctor import format_doctor_report, run_doctor
from .draft_generator import generate_draft
from .io_utils import resolve_bundle_paths, write_draft


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="episode-draft")
    subparsers = parser.add_subparsers(dest="command", required=True)

    draft_parser = subparsers.add_parser(
        "draft-from-bundle",
        help="Generate EpisodeDraft.json from an acquisition bundle.",
    )
    draft_parser.add_argument("bundle_dir", type=Path)
    draft_parser.add_argument("--output", type=Path, default=None)
    draft_parser.add_argument("--backend", choices=["auto", "local", "api", "heuristic"], default="auto")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check .env loading and model endpoint connectivity.",
    )
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def cmd_draft_from_bundle(bundle_dir: Path, output: Path | None, backend: str) -> int:
    draft = generate_draft(str(bundle_dir), backend_mode=backend)
    target = output or resolve_bundle_paths(bundle_dir)["draft"]
    result = write_draft(draft, target)
    print(result)
    return 0


def cmd_doctor(as_json: bool) -> int:
    report = run_doctor()
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_doctor_report(report))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "draft-from-bundle":
        return cmd_draft_from_bundle(args.bundle_dir, args.output, args.backend)
    if args.command == "doctor":
        return cmd_doctor(args.as_json)
    return 1


if __name__ == "__main__":
    sys.exit(main())
