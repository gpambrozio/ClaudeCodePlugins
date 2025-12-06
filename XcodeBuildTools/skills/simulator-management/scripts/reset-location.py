#!/usr/bin/env python3
"""
Reset/clear simulated GPS location on an iOS Simulator.

Usage:
    ./reset-location.py --udid <UDID>

Options:
    --udid UDID    Simulator UDID
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
    parser = argparse.ArgumentParser(description="Reset simulator GPS location")
    parser.add_argument("--udid", help="Simulator UDID")

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
            ["xcrun", "simctl", "location", simulator_udid, "clear"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Location cleared",
                "udid": simulator_udid
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Failed to clear location"
            }))
            return 1

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
