#!/usr/bin/env python3
"""
Clean Xcode derived data.

Usage:
    ./clean-derived-data.py --all
    ./clean-derived-data.py --project MyApp
    ./clean-derived-data.py --all --dry-run

Options:
    --all                 Clean all derived data
    --project NAME        Clean derived data for specific project
    --dry-run             Show what would be cleaned
    --older-than DAYS     Only clean data older than N days
"""

import argparse
import json
import os
import shutil
import sys
import time


def get_derived_data_path():
    """Get the derived data path."""
    return os.path.expanduser("~/Library/Developer/Xcode/DerivedData")


def get_folder_size(path):
    """Get folder size in bytes."""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except (OSError, IOError):
                    pass
    except (OSError, IOError):
        pass
    return total


def format_size(size_bytes):
    """Format size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description="Clean Xcode derived data")
    parser.add_argument("--all", action="store_true", help="Clean all derived data")
    parser.add_argument("--project", help="Clean derived data for specific project")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned")
    parser.add_argument("--older-than", type=int, help="Only clean data older than N days")

    args = parser.parse_args()

    if not args.all and not args.project:
        print(json.dumps({
            "success": False,
            "error": "Either --all or --project is required"
        }))
        return 1

    derived_data_path = get_derived_data_path()

    if not os.path.exists(derived_data_path):
        print(json.dumps({
            "success": True,
            "message": "No derived data found",
            "path": derived_data_path
        }))
        return 0

    # Find folders to clean
    folders_to_clean = []
    now = time.time()
    cutoff = now - (args.older_than * 86400) if args.older_than else 0

    try:
        for item in os.listdir(derived_data_path):
            item_path = os.path.join(derived_data_path, item)

            if not os.path.isdir(item_path):
                continue

            # Skip module cache
            if item.endswith(".noindex"):
                continue

            # Filter by project name if specified
            if args.project and args.project.lower() not in item.lower():
                continue

            # Check age if specified
            if args.older_than:
                mtime = os.path.getmtime(item_path)
                if mtime > cutoff:
                    continue

            size = get_folder_size(item_path)
            folders_to_clean.append({
                "name": item,
                "path": item_path,
                "size_bytes": size,
                "size": format_size(size)
            })

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1

    if not folders_to_clean:
        print(json.dumps({
            "success": True,
            "message": "No matching derived data found",
            "path": derived_data_path
        }))
        return 0

    total_size = sum(f["size_bytes"] for f in folders_to_clean)

    if args.dry_run:
        print(json.dumps({
            "success": True,
            "dry_run": True,
            "message": f"Would clean {len(folders_to_clean)} folder(s), {format_size(total_size)}",
            "folders": folders_to_clean,
            "total_size": format_size(total_size)
        }, indent=2))
        return 0

    # Actually clean
    cleaned = []
    failed = []

    for folder in folders_to_clean:
        try:
            shutil.rmtree(folder["path"])
            cleaned.append(folder["name"])
        except Exception as e:
            failed.append({"name": folder["name"], "error": str(e)})

    print(json.dumps({
        "success": len(failed) == 0,
        "message": f"Cleaned {len(cleaned)} folder(s), freed {format_size(total_size)}",
        "cleaned_count": len(cleaned),
        "cleaned": cleaned,
        "failed": failed,
        "freed_space": format_size(total_size)
    }, indent=2))

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
