#!/usr/bin/env python3
"""
Launch an app on an iOS Simulator.

Usage:
    ./launch-app-simulator.py --simulator-id <UDID> --bundle-id com.example.myapp
    ./launch-app-simulator.py --simulator-id <UDID> --bundle-id com.example.myapp --console

Options:
    --simulator-id UDID    Simulator UDID (required)
    --bundle-id ID         App bundle identifier (required)
    --console              Show console output
"""

import argparse
import json
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Launch app on iOS Simulator")
    parser.add_argument("--simulator-id", required=True, help="Simulator UDID")
    parser.add_argument("--bundle-id", required=True, help="App bundle identifier")
    parser.add_argument("--console", action="store_true", help="Show console output")

    args = parser.parse_args()

    try:
        cmd = ["xcrun", "simctl", "launch"]

        if args.console:
            cmd.append("--console")

        cmd.extend([args.simulator_id, args.bundle_id])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Try to extract PID from output
            pid = None
            output = result.stdout.strip()
            if output and output.split()[-1].isdigit():
                pid = int(output.split()[-1])

            response = {
                "success": True,
                "message": f"Launched {args.bundle_id}",
                "bundle_id": args.bundle_id,
                "simulator_id": args.simulator_id
            }
            if pid:
                response["pid"] = pid

            print(json.dumps(response, indent=2))
            return 0
        else:
            error = result.stderr or result.stdout or "Launch failed"

            # Check for common errors
            if "Unable to lookup" in error or "not found" in error.lower():
                error = f"App {args.bundle_id} is not installed on this simulator"

            print(json.dumps({
                "success": False,
                "error": error,
                "bundle_id": args.bundle_id,
                "simulator_id": args.simulator_id
            }))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Launch timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
