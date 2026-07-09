#!/usr/bin/env python3
"""Copy root common hook helpers into every local plugin package."""

import argparse
import json
import shutil
import sys
from pathlib import Path


GENERATED_MESSAGE = (
    "Generated from {source} by scripts/sync-plugin-common.py. "
    "Do not edit this copy; edit {source} and rerun scripts/sync-plugin-common.py."
)


def plugin_dirs(repo_root):
    return sorted(
        path.parent.parent
        for path in repo_root.glob("*/.claude-plugin/plugin.json")
    )


def source_files(common_dir):
    return sorted(path for path in common_dir.iterdir() if path.is_file())


def describe(path, repo_root):
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def generated_bytes(source, repo_root):
    source_ref = describe(source, repo_root)
    message = GENERATED_MESSAGE.format(source=source_ref)

    if source.suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        return json.dumps(
            {"$comment": message, **payload},
            indent=2,
        ).encode("utf-8") + b"\n"

    text = source.read_text(encoding="utf-8")
    comment = "//" if source.suffix in {".js", ".ts"} else "#"
    header = f"{comment} {message}\n"
    if text.startswith("#!"):
        first_line, separator, remainder = text.partition("\n")
        text = first_line + separator + header + remainder
    else:
        text = header + text
    return text.encode("utf-8")


def check_plugin_common(repo_root, plugin_dir, files):
    issues = []
    common_dir = plugin_dir / "common"

    if common_dir.is_symlink():
        issues.append(f"{describe(common_dir, repo_root)} is a symlink")
        return issues

    if not common_dir.is_dir():
        issues.append(f"{describe(common_dir, repo_root)} is missing")
        return issues

    expected_names = {path.name for path in files}
    actual_files = {path.name: path for path in common_dir.iterdir() if path.is_file()}

    for source in files:
        target = common_dir / source.name
        if not target.exists():
            issues.append(f"{describe(target, repo_root)} is missing")
        elif generated_bytes(source, repo_root) != target.read_bytes():
            issues.append(f"{describe(target, repo_root)} differs from {describe(source, repo_root)}")

    for extra_name in sorted(set(actual_files) - expected_names):
        issues.append(f"{describe(actual_files[extra_name], repo_root)} is stale")

    return issues


def sync_plugin_common(repo_root, plugin_dir, files):
    common_dir = plugin_dir / "common"

    if common_dir.is_symlink() or common_dir.is_file():
        common_dir.unlink()
    common_dir.mkdir(exist_ok=True)

    expected_names = {path.name for path in files}
    for child in common_dir.iterdir():
        if child.name in expected_names:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    for source in files:
        target = common_dir / source.name
        target.write_bytes(generated_bytes(source, repo_root))
        shutil.copymode(source, target)


def main():
    parser = argparse.ArgumentParser(
        description="Copy root common hook helpers into every plugin/common directory.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify plugin/common copies are current without writing files",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    common_dir = repo_root / "common"
    files = source_files(common_dir)

    if args.check:
        issues = []
        for plugin_dir in plugin_dirs(repo_root):
            issues.extend(check_plugin_common(repo_root, plugin_dir, files))
        if issues:
            for issue in issues:
                print(issue, file=sys.stderr)
            return 1
        return 0

    for plugin_dir in plugin_dirs(repo_root):
        sync_plugin_common(repo_root, plugin_dir, files)

    return 0


if __name__ == "__main__":
    sys.exit(main())
