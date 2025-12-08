#!/usr/bin/env python3
"""
Discover Xcode projects and workspaces in a directory.

Usage:
    discover-projects.py --path /path/to/scan [options]

Arguments:
    --path PATH        Path to scan for Xcode projects (required)
    --max-depth N      Maximum directory depth to scan (default: 5)

Output:
    JSON with lists of discovered .xcodeproj and .xcworkspace files
"""

import argparse
import json
import os
import sys

# Directories to skip during scanning
SKIP_DIRS = {
    'build', 'Build', 'DerivedData', 'Pods', '.git', 'node_modules',
    '.build', 'Carthage', 'vendor', '.svn', '.hg'
}


def discover_projects(path, max_depth=5):
    """Recursively discover Xcode projects and workspaces."""
    projects = []
    workspaces = []
    path = os.path.abspath(path)

    def scan_directory(dir_path, current_depth):
        if current_depth > max_depth:
            return

        try:
            entries = os.listdir(dir_path)
        except PermissionError:
            return
        except OSError:
            return

        for entry in entries:
            full_path = os.path.join(dir_path, entry)

            # Skip symbolic links
            if os.path.islink(full_path):
                continue

            # Check for Xcode bundles
            if entry.endswith('.xcodeproj'):
                projects.append(full_path)
                continue  # Don't descend into xcodeproj

            if entry.endswith('.xcworkspace'):
                # Skip internal workspace files
                if 'xcodeproj' not in dir_path.lower():
                    workspaces.append(full_path)
                continue  # Don't descend into xcworkspace

            # Recurse into directories
            if os.path.isdir(full_path):
                if entry not in SKIP_DIRS and not entry.startswith('.'):
                    scan_directory(full_path, current_depth + 1)

    scan_directory(path, 0)

    return sorted(projects), sorted(workspaces)


def main():
    parser = argparse.ArgumentParser(description="Discover Xcode projects and workspaces")
    parser.add_argument("--path", required=True, help="Path to scan")
    parser.add_argument("--max-depth", type=int, default=5, help="Maximum scan depth")

    args = parser.parse_args()

    scan_path = os.path.abspath(args.path)

    if not os.path.isdir(scan_path):
        print(json.dumps({
            "success": False,
            "error": f"Path does not exist or is not a directory: {scan_path}"
        }))
        sys.exit(1)

    projects, workspaces = discover_projects(scan_path, args.max_depth)

    result = {
        "success": True,
        "scan_path": scan_path,
        "max_depth": args.max_depth,
        "projects": {
            "count": len(projects),
            "paths": projects
        },
        "workspaces": {
            "count": len(workspaces),
            "paths": workspaces
        }
    }

    if not projects and not workspaces:
        result["message"] = "No Xcode projects or workspaces found"
    else:
        result["message"] = f"Found {len(projects)} project(s) and {len(workspaces)} workspace(s)"

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
