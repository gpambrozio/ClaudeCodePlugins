#!/usr/bin/env python3
"""
Boot an iOS Simulator.

Usage:
    ./boot-simulator.py --name "iPhone 15"
    ./boot-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    ./boot-simulator.py --name "iPhone 15" --headless

Options:
    --name NAME     Simulator device name
    --udid UDID     Simulator UDID
    --headless      Don't open Simulator.app window
"""

import argparse
import json
import subprocess
import sys


def find_simulator_by_name(name):
    """Find a simulator by name, preferring latest runtime."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, "Failed to list simulators"

        data = json.loads(result.stdout)
        runtimes = {r["identifier"]: r["name"] for r in data.get("runtimes", [])}

        matches = []
        for runtime_id, device_list in data.get("devices", {}).items():
            runtime_name = runtimes.get(runtime_id, "")
            for device in device_list:
                if device.get("name") == name and device.get("isAvailable", False):
                    matches.append({
                        "udid": device.get("udid"),
                        "runtime": runtime_name,
                        "state": device.get("state")
                    })

        if not matches:
            return None, f"No simulator named '{name}' found"

        # Sort by runtime (newest first)
        matches.sort(key=lambda x: x["runtime"], reverse=True)
        return matches[0], None

    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Boot iOS Simulator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", help="Simulator device name")
    group.add_argument("--udid", help="Simulator UDID")
    parser.add_argument("--headless", action="store_true", help="Don't open Simulator.app")

    args = parser.parse_args()

    # Get simulator UDID
    simulator_udid = args.udid
    simulator_info = None

    if args.name:
        simulator_info, error = find_simulator_by_name(args.name)
        if error:
            print(json.dumps({"success": False, "error": error}))
            return 1
        simulator_udid = simulator_info["udid"]

        # Check if already booted
        if simulator_info["state"] == "Booted":
            print(json.dumps({
                "success": True,
                "message": "Simulator is already booted",
                "udid": simulator_udid,
                "name": args.name,
                "runtime": simulator_info["runtime"]
            }, indent=2))
            return 0

    try:
        # Boot the simulator
        result = subprocess.run(
            ["xcrun", "simctl", "boot", simulator_udid],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            # Check if already booted
            if "Unable to boot device in current state: Booted" in result.stderr:
                response = {
                    "success": True,
                    "message": "Simulator is already booted",
                    "udid": simulator_udid
                }
                if simulator_info:
                    response["name"] = args.name
                    response["runtime"] = simulator_info["runtime"]
                print(json.dumps(response, indent=2))
                return 0
            else:
                print(json.dumps({
                    "success": False,
                    "error": result.stderr or "Failed to boot simulator"
                }))
                return 1

        # Open Simulator.app unless headless
        if not args.headless:
            subprocess.run(
                ["open", "-a", "Simulator", "--args", "-CurrentDeviceUDID", simulator_udid],
                capture_output=True,
                timeout=10
            )

        response = {
            "success": True,
            "message": "Simulator booted successfully",
            "udid": simulator_udid
        }
        if simulator_info:
            response["name"] = args.name
            response["runtime"] = simulator_info["runtime"]

        print(json.dumps(response, indent=2))
        return 0

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Boot timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
