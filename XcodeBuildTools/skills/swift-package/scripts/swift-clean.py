#!/usr/bin/env python3
"""
Clean Swift package build artifacts.

Usage:
    ./swift-clean.py --path /path/to/package
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Clean Swift package")
    parser.add_argument("--path", default=".", help="Path to Swift package")

    args = parser.parse_args()

    # Resolve and validate path
    package_path = os.path.abspath(args.path)
    package_swift = os.path.join(package_path, "Package.swift")

    if not os.path.exists(package_swift):
        print(json.dumps({
            "success": False,
            "error": f"No Package.swift found at {package_path}"
        }))
        return 1

    try:
        result = subprocess.run(
            ["swift", "package", "clean", "--package-path", package_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Package cleaned",
                "path": package_path
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Clean failed"
            }))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Clean timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
