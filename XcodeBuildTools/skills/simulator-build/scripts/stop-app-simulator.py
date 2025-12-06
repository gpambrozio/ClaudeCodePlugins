#!/usr/bin/env python3
"""
Terminate an app on an iOS Simulator.

Usage:
    ./stop-app-simulator.py --simulator-id <UDID> --bundle-id com.example.myapp

Options:
    --simulator-id UDID    Simulator UDID (required)
    --bundle-id ID         App bundle identifier (required)
"""

import argparse
import json
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Stop app on iOS Simulator")
    parser.add_argument("--simulator-id", required=True, help="Simulator UDID")
    parser.add_argument("--bundle-id", required=True, help="App bundle identifier")

    args = parser.parse_args()

    try:
        result = subprocess.run(
            ["xcrun", "simctl", "terminate", args.simulator_id, args.bundle_id],
            capture_output=True,
            text=True,
            timeout=30
        )

        # simctl terminate returns 0 even if app wasn't running
        print(json.dumps({
            "success": True,
            "message": f"Terminated {args.bundle_id}",
            "bundle_id": args.bundle_id,
            "simulator_id": args.simulator_id
        }, indent=2))
        return 0

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Terminate timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
