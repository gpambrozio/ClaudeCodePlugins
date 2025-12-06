#!/usr/bin/env python3
"""
Clean various Xcode caches.

Usage:
    ./clean-caches.py --module-cache
    ./clean-caches.py --package-cache
    ./clean-caches.py --all

Options:
    --module-cache     Clean Swift/Clang module cache
    --package-cache    Clean Swift Package Manager cache
    --all              Clean all caches
    --dry-run          Show what would be cleaned
"""

import argparse
import json
import os
import shutil
import sys


CACHE_PATHS = {
    "module_cache": os.path.expanduser("~/Library/Developer/Xcode/DerivedData/ModuleCache.noindex"),
    "package_cache": os.path.expanduser("~/Library/Caches/org.swift.swiftpm"),
    "swift_build_cache": os.path.expanduser("~/Library/Developer/Xcode/DerivedData/SourcePackages"),
}


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


def clean_cache(name, path, dry_run=False):
    """Clean a specific cache."""
    if not os.path.exists(path):
        return {
            "name": name,
            "path": path,
            "status": "not_found",
            "message": "Cache not found"
        }

    size = get_folder_size(path)

    if dry_run:
        return {
            "name": name,
            "path": path,
            "status": "would_clean",
            "size": format_size(size),
            "size_bytes": size
        }

    try:
        shutil.rmtree(path)
        return {
            "name": name,
            "path": path,
            "status": "cleaned",
            "freed": format_size(size),
            "size_bytes": size
        }
    except Exception as e:
        return {
            "name": name,
            "path": path,
            "status": "error",
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Clean Xcode caches")
    parser.add_argument("--module-cache", action="store_true", help="Clean module cache")
    parser.add_argument("--package-cache", action="store_true", help="Clean SPM cache")
    parser.add_argument("--all", action="store_true", help="Clean all caches")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned")

    args = parser.parse_args()

    if not args.all and not args.module_cache and not args.package_cache:
        print(json.dumps({
            "success": False,
            "error": "Specify --module-cache, --package-cache, or --all"
        }))
        return 1

    caches_to_clean = []

    if args.all or args.module_cache:
        caches_to_clean.append(("module_cache", CACHE_PATHS["module_cache"]))

    if args.all or args.package_cache:
        caches_to_clean.append(("package_cache", CACHE_PATHS["package_cache"]))

    results = []
    total_freed = 0

    for name, path in caches_to_clean:
        result = clean_cache(name, path, args.dry_run)
        results.append(result)
        if result.get("size_bytes"):
            total_freed += result["size_bytes"]

    success = all(r.get("status") != "error" for r in results)

    response = {
        "success": success,
        "dry_run": args.dry_run,
        "caches": results,
        "total_freed": format_size(total_freed)
    }

    if args.dry_run:
        response["message"] = f"Would free {format_size(total_freed)}"
    else:
        response["message"] = f"Freed {format_size(total_freed)}"

    print(json.dumps(response, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
