#!/usr/bin/env python3
"""
Shutdown iOS Simulator(s).

Usage:
    ./shutdown-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    ./shutdown-simulator.py --all

Options:
    --udid UDID     Simulator UDID to shutdown
    --all           Shutdown all simulators
"""

import argparse
import json
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Shutdown iOS Simulator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--udid", help="Simulator UDID")
    group.add_argument("--all", action="store_true", help="Shutdown all simulators")

    args = parser.parse_args()

    try:
        if args.all:
            result = subprocess.run(
                ["xcrun", "simctl", "shutdown", "all"],
                capture_output=True,
                text=True,
                timeout=60
            )

            print(json.dumps({
                "success": True,
                "message": "All simulators shutdown"
            }, indent=2))
            return 0
        else:
            result = subprocess.run(
                ["xcrun", "simctl", "shutdown", args.udid],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # Already shutdown is OK
                if "current state: Shutdown" in result.stderr:
                    print(json.dumps({
                        "success": True,
                        "message": "Simulator is already shutdown",
                        "udid": args.udid
                    }, indent=2))
                    return 0
                else:
                    print(json.dumps({
                        "success": False,
                        "error": result.stderr or "Failed to shutdown"
                    }))
                    return 1

            print(json.dumps({
                "success": True,
                "message": "Simulator shutdown",
                "udid": args.udid
            }, indent=2))
            return 0

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Shutdown timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
