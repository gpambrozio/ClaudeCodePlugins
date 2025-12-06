#!/usr/bin/env python3
"""
Clean Swift Package build artifacts using `swift package clean`.

Usage:
    swift-package-clean.py --package-path /path/to/package

Arguments:
    --package-path PATH    Path to the Swift package root (required)

Output:
    JSON with success status and message
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Clean Swift Package build artifacts")
    parser.add_argument("--package-path", required=True, help="Path to Swift package root")

    args = parser.parse_args()

    # Resolve to absolute path
    package_path = os.path.abspath(args.package_path)

    if not os.path.isdir(package_path):
        print(json.dumps({
            "success": False,
            "error": f"Package path does not exist: {package_path}"
        }))
        sys.exit(1)

    # Build command
    cmd = ["swift", "package", "--package-path", package_path, "clean"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=package_path
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Build artifacts cleaned successfully",
                "package_path": package_path,
                "note": "The .build directory and derived data have been removed"
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": "Clean failed",
                "stderr": result.stderr.strip(),
                "stdout": result.stdout.strip()
            }))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
