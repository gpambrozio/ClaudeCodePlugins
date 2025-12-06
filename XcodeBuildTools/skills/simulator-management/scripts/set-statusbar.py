#!/usr/bin/env python3
"""
Override simulator status bar display.

Usage:
    ./set-statusbar.py --udid <UDID> --time "9:41" --battery 100 --wifi 3 --cellular 4
    ./set-statusbar.py --udid <UDID> --clear

Options:
    --udid UDID          Simulator UDID
    --time TIME          Status bar time (e.g., "9:41")
    --battery LEVEL      Battery percentage (0-100)
    --wifi BARS          WiFi signal bars (0-3)
    --cellular BARS      Cellular signal bars (0-4)
    --clear              Remove all status bar overrides
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
    parser = argparse.ArgumentParser(description="Set simulator status bar")
    parser.add_argument("--udid", help="Simulator UDID")
    parser.add_argument("--time", help="Status bar time (e.g., '9:41')")
    parser.add_argument("--battery", type=int, help="Battery percentage (0-100)")
    parser.add_argument("--wifi", type=int, choices=[0, 1, 2, 3], help="WiFi signal bars")
    parser.add_argument("--cellular", type=int, choices=[0, 1, 2, 3, 4], help="Cellular signal bars")
    parser.add_argument("--clear", action="store_true", help="Clear all overrides")

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
        if args.clear:
            result = subprocess.run(
                ["xcrun", "simctl", "status_bar", simulator_udid, "clear"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(json.dumps({
                    "success": True,
                    "message": "Status bar overrides cleared",
                    "udid": simulator_udid
                }, indent=2))
                return 0
            else:
                print(json.dumps({
                    "success": False,
                    "error": result.stderr or "Failed to clear status bar"
                }))
                return 1

        # Build override command
        cmd = ["xcrun", "simctl", "status_bar", simulator_udid, "override"]

        settings = {}

        if args.time:
            cmd.extend(["--time", args.time])
            settings["time"] = args.time

        if args.battery is not None:
            if args.battery < 0 or args.battery > 100:
                print(json.dumps({
                    "success": False,
                    "error": "Battery must be between 0 and 100"
                }))
                return 1
            cmd.extend(["--batteryLevel", str(args.battery)])
            cmd.extend(["--batteryState", "charged" if args.battery == 100 else "charging"])
            settings["battery"] = args.battery

        if args.wifi is not None:
            cmd.extend(["--wifiBars", str(args.wifi)])
            cmd.extend(["--wifiMode", "active"])
            settings["wifi"] = args.wifi

        if args.cellular is not None:
            cmd.extend(["--cellularBars", str(args.cellular)])
            cmd.extend(["--cellularMode", "active"])
            settings["cellular"] = args.cellular

        if not settings:
            print(json.dumps({
                "success": False,
                "error": "No status bar settings provided. Use --time, --battery, --wifi, --cellular, or --clear"
            }))
            return 1

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Status bar overridden",
                "settings": settings,
                "udid": simulator_udid
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Failed to override status bar"
            }))
            return 1

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
