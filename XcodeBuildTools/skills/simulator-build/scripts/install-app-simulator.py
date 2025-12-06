#!/usr/bin/env python3
"""
Install an app on an iOS Simulator.

Usage:
    ./install-app-simulator.py --simulator-id <UDID> --app /path/to/MyApp.app

Options:
    --simulator-id UDID    Simulator UDID (required)
    --app PATH             Path to .app bundle (required)
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Install app on iOS Simulator")
    parser.add_argument("--simulator-id", required=True, help="Simulator UDID")
    parser.add_argument("--app", required=True, help="Path to .app bundle")

    args = parser.parse_args()

    # Validate app path
    if not os.path.exists(args.app):
        print(json.dumps({"success": False, "error": f"App bundle not found: {args.app}"}))
        return 1

    if not args.app.endswith(".app"):
        print(json.dumps({"success": False, "error": "Path must point to a .app bundle"}))
        return 1

    try:
        result = subprocess.run(
            ["xcrun", "simctl", "install", args.simulator_id, args.app],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": f"App installed on simulator {args.simulator_id}",
                "simulator_id": args.simulator_id,
                "app_path": args.app
            }, indent=2))
            return 0
        else:
            error = result.stderr or result.stdout or "Installation failed"
            print(json.dumps({
                "success": False,
                "error": error,
                "simulator_id": args.simulator_id
            }))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Installation timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
