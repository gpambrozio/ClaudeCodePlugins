#!/usr/bin/env python3
"""
Launch a macOS application.

Usage:
    launch-mac-app.py --app /path/to/MyApp.app [--args ...]

Arguments:
    --app PATH     Path to the .app bundle to launch
    --args ARGS    Optional arguments to pass to the app

Output:
    JSON with launch status
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Launch a macOS application")
    parser.add_argument("--app", required=True, help="Path to .app bundle")
    parser.add_argument("--args", nargs="*", default=[], help="Arguments to pass to the app")

    args = parser.parse_args()

    app_path = os.path.abspath(args.app)

    # Validate app path
    if not os.path.isdir(app_path):
        print(json.dumps({
            "success": False,
            "error": f"App bundle not found: {app_path}"
        }))
        sys.exit(1)

    if not app_path.endswith('.app'):
        print(json.dumps({
            "success": False,
            "error": "Path must be a .app bundle"
        }))
        sys.exit(1)

    # Build command
    cmd = ["open", app_path]

    if args.args:
        cmd.append("--args")
        cmd.extend(args.args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "App launched successfully",
                "app_path": app_path
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr.strip() or "Failed to launch app",
                "app_path": app_path
            }))
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "success": False,
            "error": "Launch timed out"
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
