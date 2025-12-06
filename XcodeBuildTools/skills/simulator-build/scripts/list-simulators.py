#!/usr/bin/env python3
"""
List available iOS simulators.

Usage:
    ./list-simulators.py [--booted] [--runtime RUNTIME]

Options:
    --booted          List only booted simulators
    --runtime RUNTIME Filter by runtime (e.g., "iOS 17")
"""

import argparse
import json
import subprocess
import sys


def get_simulators():
    """Get simulator list from simctl."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, result.stderr

        return json.loads(result.stdout), None

    except subprocess.TimeoutExpired:
        return None, "Command timed out"
    except json.JSONDecodeError as e:
        return None, f"Failed to parse JSON: {e}"
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="List iOS simulators")
    parser.add_argument("--booted", action="store_true", help="List only booted simulators")
    parser.add_argument("--runtime", help="Filter by runtime (e.g., 'iOS 17')")

    args = parser.parse_args()

    data, error = get_simulators()

    if data is None:
        print(json.dumps({"success": False, "error": error}))
        return 1

    # Build runtime lookup
    runtimes = {}
    for runtime in data.get("runtimes", []):
        runtimes[runtime.get("identifier", "")] = runtime.get("name", "Unknown")

    # Collect simulators
    simulators = []
    devices = data.get("devices", {})

    for runtime_id, device_list in devices.items():
        runtime_name = runtimes.get(runtime_id, runtime_id)

        # Filter by runtime if specified
        if args.runtime and args.runtime.lower() not in runtime_name.lower():
            continue

        for device in device_list:
            state = device.get("state", "Unknown")

            # Filter booted only if specified
            if args.booted and state != "Booted":
                continue

            simulators.append({
                "name": device.get("name", "Unknown"),
                "udid": device.get("udid", "Unknown"),
                "state": state,
                "runtime": runtime_name,
                "is_available": device.get("isAvailable", False)
            })

    # Sort by runtime (newest first) then by name
    simulators.sort(key=lambda x: (x["runtime"], x["name"]), reverse=True)

    result = {
        "success": True,
        "count": len(simulators),
        "simulators": simulators
    }

    if len(simulators) == 0:
        if args.booted:
            result["message"] = "No booted simulators. Use simulator-management skill to boot one."
        else:
            result["message"] = "No simulators available. Install simulator runtimes in Xcode."

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
