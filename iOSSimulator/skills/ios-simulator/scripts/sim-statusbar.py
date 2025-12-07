#!/usr/bin/env python3
"""
Override the iOS simulator status bar for clean screenshots.

Usage:
    sim-statusbar.py --udid SIMULATOR_UDID [options]
    sim-statusbar.py --udid SIMULATOR_UDID --clear

Arguments:
    --udid UDID           Simulator UDID
    --time TIME           Override time (e.g., "9:41")
    --battery LEVEL       Battery level percentage (0-100)
    --battery-state STATE Battery state: charged, charging, discharging
    --wifi BARS           WiFi signal bars (0-3)
    --cellular BARS       Cellular signal bars (0-4)
    --carrier NAME        Carrier name
    --clear               Clear all status bar overrides

Output:
    JSON with status
"""

import argparse
import json
import subprocess
import sys


def set_status_bar(udid, options):
    """Set status bar overrides."""
    cmd = ["xcrun", "simctl", "status_bar", udid, "override"]

    if options.get("time"):
        cmd.extend(["--time", options["time"]])

    if options.get("battery") is not None:
        cmd.extend(["--batteryLevel", str(options["battery"])])

    if options.get("battery_state"):
        cmd.extend(["--batteryState", options["battery_state"]])

    if options.get("wifi") is not None:
        cmd.extend(["--wifiBars", str(options["wifi"])])

    if options.get("cellular") is not None:
        cmd.extend(["--cellularBars", str(options["cellular"])])

    if options.get("carrier"):
        cmd.extend(["--operatorName", options["carrier"]])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return True, "Status bar overrides applied"
        else:
            return False, result.stderr.strip() or "Failed to set status bar"

    except Exception as e:
        return False, str(e)


def clear_status_bar(udid):
    """Clear all status bar overrides."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "status_bar", udid, "clear"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return True, "Status bar overrides cleared"
        else:
            return False, result.stderr.strip() or "Failed to clear status bar"

    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Override simulator status bar")
    parser.add_argument("--udid", required=True, help="Simulator UDID")
    parser.add_argument("--time", help="Override time (e.g., '9:41')")
    parser.add_argument("--battery", type=int, choices=range(0, 101), metavar="0-100",
                        help="Battery level percentage")
    parser.add_argument("--battery-state", choices=["charged", "charging", "discharging"],
                        help="Battery state")
    parser.add_argument("--wifi", type=int, choices=range(0, 4), metavar="0-3",
                        help="WiFi signal bars")
    parser.add_argument("--cellular", type=int, choices=range(0, 5), metavar="0-4",
                        help="Cellular signal bars")
    parser.add_argument("--carrier", help="Carrier name")
    parser.add_argument("--clear", action="store_true", help="Clear all overrides")

    args = parser.parse_args()

    if args.clear:
        success, message = clear_status_bar(args.udid)
    else:
        options = {
            "time": args.time,
            "battery": args.battery,
            "battery_state": args.battery_state,
            "wifi": args.wifi,
            "cellular": args.cellular,
            "carrier": args.carrier
        }

        # Check if any options were provided
        if not any(v is not None for v in options.values()):
            print(json.dumps({
                "success": False,
                "error": "No status bar options provided. Use --clear to reset, or specify options like --time, --battery, etc."
            }))
            sys.exit(1)

        success, message = set_status_bar(args.udid, options)

    if success:
        print(json.dumps({
            "success": True,
            "message": message,
            "udid": args.udid
        }))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "udid": args.udid
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
