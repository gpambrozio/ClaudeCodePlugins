#!/usr/bin/env python3
"""
Discover Xcode projects and workspaces in a directory.

Usage:
    ./discover-projects.py [--path PATH] [--recursive]

Options:
    --path PATH     Directory to search (default: current directory)
    --recursive     Search subdirectories
"""

import argparse
import json
import os
import sys


def find_xcode_items(path, recursive=False):
    """Find .xcworkspace and .xcodeproj items."""
    items = []

    if recursive:
        for root, dirs, files in os.walk(path):
            # Skip hidden directories and common non-project dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['Pods', 'Carthage', 'node_modules']]

            for d in list(dirs):
                if d.endswith('.xcworkspace'):
                    items.append({
                        "type": "workspace",
                        "name": d,
                        "path": os.path.join(root, d)
                    })
                    # Don't descend into workspace
                    dirs.remove(d)
                elif d.endswith('.xcodeproj'):
                    items.append({
                        "type": "project",
                        "name": d,
                        "path": os.path.join(root, d)
                    })
                    # Don't descend into project
                    dirs.remove(d)
    else:
        try:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    if item.endswith('.xcworkspace'):
                        items.append({
                            "type": "workspace",
                            "name": item,
                            "path": full_path
                        })
                    elif item.endswith('.xcodeproj'):
                        items.append({
                            "type": "project",
                            "name": item,
                            "path": full_path
                        })
        except PermissionError:
            pass

    # Sort: workspaces first, then by name
    items.sort(key=lambda x: (0 if x["type"] == "workspace" else 1, x["name"]))

    return items


def main():
    parser = argparse.ArgumentParser(description="Discover Xcode projects")
    parser.add_argument("--path", default=".", help="Directory to search")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories")

    args = parser.parse_args()

    # Resolve path
    search_path = os.path.abspath(args.path)

    if not os.path.exists(search_path):
        print(json.dumps({"success": False, "error": f"Path not found: {search_path}"}))
        return 1

    if not os.path.isdir(search_path):
        print(json.dumps({"success": False, "error": f"Not a directory: {search_path}"}))
        return 1

    items = find_xcode_items(search_path, args.recursive)

    result = {
        "success": True,
        "search_path": search_path,
        "recursive": args.recursive,
        "count": len(items),
        "projects": items
    }

    if len(items) == 0:
        result["message"] = "No Xcode projects or workspaces found"

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
