#!/usr/bin/env python3
"""
Set simulator appearance (light/dark mode).

Usage:
    ./set-appearance.py --udid <UDID> --mode dark
    ./set-appearance.py --udid <UDID> --mode light

Options:
    --udid UDID    Simulator UDID
    --mode MODE    Appearance mode (light or dark)
"""

import argparse
import json
import subprocess
import sys


def get_booted_simulator():
    """Get the first booted simulator."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("state") == "Booted":
                    return device.get("udid")

        return None

    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Set simulator appearance")
    parser.add_argument("--udid", help="Simulator UDID")
    parser.add_argument("--mode", required=True, choices=["light", "dark"], help="Appearance mode")

    args = parser.parse_args()

    # Get simulator UDID
    simulator_udid = args.udid
    if not simulator_udid:
        simulator_udid = get_booted_simulator()
        if not simulator_udid:
            print(json.dumps({
                "success": False,
                "error": "No booted simulator found. Specify --udid or boot a simulator first."
            }))
            return 1

    try:
        result = subprocess.run(
            ["xcrun", "simctl", "ui", simulator_udid, "appearance", args.mode],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": f"Appearance set to {args.mode}",
                "mode": args.mode,
                "udid": simulator_udid
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Failed to set appearance"
            }))
            return 1

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
