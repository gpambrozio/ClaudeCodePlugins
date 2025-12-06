#!/usr/bin/env python3
"""
Open the Simulator.app window for a simulator.

Usage:
    ./open-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    ./open-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" --focus

Options:
    --udid UDID     Simulator UDID
    --focus         Bring Simulator.app to front
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
    parser = argparse.ArgumentParser(description="Open Simulator.app")
    parser.add_argument("--udid", help="Simulator UDID")
    parser.add_argument("--focus", action="store_true", help="Bring to front")

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
        cmd = ["open"]

        if args.focus:
            cmd.append("-a")
            cmd.append("Simulator")
        else:
            cmd.extend(["-a", "Simulator", "--args", "-CurrentDeviceUDID", simulator_udid])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Simulator.app opened",
                "udid": simulator_udid
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Failed to open Simulator.app"
            }))
            return 1

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
