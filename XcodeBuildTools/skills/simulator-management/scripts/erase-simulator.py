#!/usr/bin/env python3
"""
Erase iOS Simulator(s) - reset to factory settings.

Usage:
    ./erase-simulator.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    ./erase-simulator.py --all
    ./erase-simulator.py --runtime "iOS 17"

Options:
    --udid UDID       Erase specific simulator
    --all             Erase all simulators
    --runtime RUNTIME Erase simulators matching runtime (e.g., "iOS 17")
"""

import argparse
import json
import subprocess
import sys


def get_simulators_by_runtime(runtime_filter):
    """Get simulators matching a runtime filter."""
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
            if runtime_filter.lower() in runtime_name.lower():
                for device in device_list:
                    if device.get("isAvailable", False):
                        matches.append({
                            "udid": device.get("udid"),
                            "name": device.get("name"),
                            "runtime": runtime_name
                        })

        return matches, None

    except Exception as e:
        return None, str(e)


def erase_simulator(udid):
    """Erase a single simulator."""
    result = subprocess.run(
        ["xcrun", "simctl", "erase", udid],
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.returncode == 0, result.stderr


def main():
    parser = argparse.ArgumentParser(description="Erase iOS Simulator(s)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--udid", help="Simulator UDID")
    group.add_argument("--all", action="store_true", help="Erase all simulators")
    group.add_argument("--runtime", help="Erase simulators matching runtime")

    args = parser.parse_args()

    try:
        if args.all:
            # Shutdown all first
            subprocess.run(
                ["xcrun", "simctl", "shutdown", "all"],
                capture_output=True,
                timeout=60
            )

            result = subprocess.run(
                ["xcrun", "simctl", "erase", "all"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print(json.dumps({
                    "success": True,
                    "message": "All simulators erased"
                }, indent=2))
                return 0
            else:
                print(json.dumps({
                    "success": False,
                    "error": result.stderr or "Failed to erase simulators"
                }))
                return 1

        elif args.runtime:
            simulators, error = get_simulators_by_runtime(args.runtime)
            if error:
                print(json.dumps({"success": False, "error": error}))
                return 1

            if not simulators:
                print(json.dumps({
                    "success": False,
                    "error": f"No simulators found matching runtime '{args.runtime}'"
                }))
                return 1

            # Shutdown and erase each
            erased = []
            failed = []

            for sim in simulators:
                subprocess.run(
                    ["xcrun", "simctl", "shutdown", sim["udid"]],
                    capture_output=True,
                    timeout=30
                )

                success, error = erase_simulator(sim["udid"])
                if success:
                    erased.append(sim["name"])
                else:
                    failed.append({"name": sim["name"], "error": error})

            print(json.dumps({
                "success": len(failed) == 0,
                "erased": erased,
                "erased_count": len(erased),
                "failed": failed
            }, indent=2))
            return 0 if len(failed) == 0 else 1

        else:
            # Shutdown first
            subprocess.run(
                ["xcrun", "simctl", "shutdown", args.udid],
                capture_output=True,
                timeout=30
            )

            success, error = erase_simulator(args.udid)

            if success:
                print(json.dumps({
                    "success": True,
                    "message": "Simulator erased",
                    "udid": args.udid
                }, indent=2))
                return 0
            else:
                print(json.dumps({
                    "success": False,
                    "error": error or "Failed to erase simulator"
                }))
                return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Operation timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
