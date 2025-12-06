#!/usr/bin/env python3
"""
Stop/terminate a running macOS application.

Usage:
    ./stop-app.py --bundle-id com.example.myapp
    ./stop-app.py --bundle-id com.example.myapp --force
"""

import argparse
import json
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Stop macOS app")
    parser.add_argument("--bundle-id", required=True, help="App bundle identifier")
    parser.add_argument("--force", action="store_true", help="Force quit (kill)")

    args = parser.parse_args()

    try:
        # First try AppleScript for graceful quit
        if not args.force:
            script = f'tell application id "{args.bundle_id}" to quit'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(json.dumps({
                    "success": True,
                    "message": f"Quit {args.bundle_id}",
                    "bundle_id": args.bundle_id
                }, indent=2))
                return 0

        # Force kill using pkill
        result = subprocess.run(
            ["pkill", "-f", args.bundle_id],
            capture_output=True,
            text=True,
            timeout=10
        )

        # pkill returns 1 if no processes matched, which is OK
        print(json.dumps({
            "success": True,
            "message": f"Terminated {args.bundle_id}",
            "bundle_id": args.bundle_id,
            "forced": args.force or result.returncode != 0
        }, indent=2))
        return 0

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
