"""CLI for validating and exporting episode review packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .exporters import export_package
from .io_utils import load_package
from .rules import ALLOWED_MAINSTREAM_MEDIA, OFFICIAL_SOURCE_HINTS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shuiqian-review")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an episode package JSON file.")
    validate_parser.add_argument("package_path", type=Path)

    export_parser = subparsers.add_parser("export", help="Export markdown production files.")
    export_parser.add_argument("package_path", type=Path)
    export_parser.add_argument("--output", type=Path, default=Path("out"))

    init_parser = subparsers.add_parser("init", help="Create a new episode package from the template.")
    init_parser.add_argument("output_path", type=Path)

    subparsers.add_parser("list-sources", help="Print allowed mainstream sources and official domain hints.")
    return parser


def cmd_validate(package_path: Path) -> int:
    package = load_package(package_path)
    issues = package.validate()
    if not issues:
        print("VALID")
        return 0

    exit_code = 0
    for issue in issues:
        print(f"{issue.level.upper()} {issue.path} {issue.message}")
        if issue.level == "error":
            exit_code = 1
    return exit_code


def cmd_export(package_path: Path, output: Path) -> int:
    package = load_package(package_path)
    issues = package.validate()
    error_count = sum(1 for item in issues if item.level == "error")
    if error_count:
        for issue in issues:
            print(f"{issue.level.upper()} {issue.path} {issue.message}")
        print("EXPORT_ABORTED validation_errors_present")
        return 1

    generated = export_package(package, output)
    for path in generated:
        print(path)
    return 0


def cmd_list_sources() -> int:
    print("Allowed mainstream media:")
    for item in sorted(ALLOWED_MAINSTREAM_MEDIA):
        print(f"- {item}")
    print("Official domain hints:")
    for item in OFFICIAL_SOURCE_HINTS:
        print(f"- {item}")
    return 0


def cmd_init(output_path: Path) -> int:
    template_path = Path(__file__).resolve().parents[2] / "templates" / "episode_template.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(output_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        return cmd_validate(args.package_path)
    if args.command == "export":
        return cmd_export(args.package_path, args.output)
    if args.command == "init":
        return cmd_init(args.output_path)
    if args.command == "list-sources":
        return cmd_list_sources()
    return 1


if __name__ == "__main__":
    sys.exit(main())
