#!/usr/bin/env python3
"""
Launch a macOS application.

Usage:
    ./launch-app.py --app /path/to/MyApp.app
    ./launch-app.py --bundle-id com.example.myapp
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Launch macOS app")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--app", help="Path to .app bundle")
    group.add_argument("--bundle-id", help="App bundle identifier")

    args = parser.parse_args()

    try:
        if args.app:
            if not os.path.exists(args.app):
                print(json.dumps({"success": False, "error": f"App not found: {args.app}"}))
                return 1

            result = subprocess.run(
                ["open", args.app],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(json.dumps({
                    "success": True,
                    "message": f"Launched {os.path.basename(args.app)}",
                    "app_path": args.app
                }, indent=2))
                return 0
            else:
                print(json.dumps({
                    "success": False,
                    "error": result.stderr or "Failed to launch app"
                }))
                return 1

        else:
            result = subprocess.run(
                ["open", "-b", args.bundle_id],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(json.dumps({
                    "success": True,
                    "message": f"Launched {args.bundle_id}",
                    "bundle_id": args.bundle_id
                }, indent=2))
                return 0
            else:
                print(json.dumps({
                    "success": False,
                    "error": result.stderr or f"Failed to launch {args.bundle_id}"
                }))
                return 1

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
