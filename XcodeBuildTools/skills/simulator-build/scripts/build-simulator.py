#!/usr/bin/env python3
"""
Build an Xcode project/workspace for iOS Simulator.

Usage:
    ./build-simulator.py --workspace MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15"
    ./build-simulator.py --project MyApp.xcodeproj --scheme MyApp --simulator-id <UDID>

Options:
    --workspace PATH       Path to .xcworkspace file
    --project PATH         Path to .xcodeproj file
    --scheme NAME          Build scheme name (required)
    --simulator-name NAME  Simulator device name
    --simulator-id UDID    Simulator UDID
    --configuration CFG    Build configuration (default: Debug)
    --use-latest-os        Use latest OS version for simulator name
    --derived-data PATH    Custom derived data path
    --extra-args ARGS      Additional xcodebuild arguments (comma-separated)
"""

import argparse
import json
import subprocess
import sys
import os


def find_simulator(name=None, udid=None, use_latest_os=False):
    """Find a simulator by name or UDID."""
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

        # If UDID provided, find it directly
        if udid:
            for runtime_devices in data.get("devices", {}).values():
                for device in runtime_devices:
                    if device.get("udid") == udid:
                        return device.get("udid"), None
            return None, f"Simulator with UDID {udid} not found"

        # Find by name
        if name:
            matches = []
            runtimes = {r["identifier"]: r["name"] for r in data.get("runtimes", [])}

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

            # Sort by runtime (newest first) - iOS 17 > iOS 16
            matches.sort(key=lambda x: x["runtime"], reverse=True)

            if use_latest_os:
                return matches[0]["udid"], None

            # Prefer booted simulator, otherwise use latest
            for m in matches:
                if m["state"] == "Booted":
                    return m["udid"], None

            return matches[0]["udid"], None

        return None, "Either --simulator-name or --simulator-id is required"

    except Exception as e:
        return None, str(e)


def run_xcodebuild(args, timeout=600):
    """Run xcodebuild and return parsed result."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        errors = []
        warnings = []

        for line in result.stdout.split("\n") + result.stderr.split("\n"):
            if ": error:" in line:
                errors.append(line.strip())
            elif ": warning:" in line:
                warnings.append(line.strip())

        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "errors": errors[:20],
            "warnings": warnings[:20],
            "error_count": len(errors),
            "warning_count": len(warnings)
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Build timed out after 10 minutes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Build for iOS Simulator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Build scheme")

    sim_group = parser.add_mutually_exclusive_group(required=True)
    sim_group.add_argument("--simulator-name", help="Simulator device name")
    sim_group.add_argument("--simulator-id", help="Simulator UDID")

    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--use-latest-os", action="store_true", help="Use latest OS for simulator name")
    parser.add_argument("--derived-data", help="Derived data path")
    parser.add_argument("--extra-args", help="Extra xcodebuild args (comma-separated)")

    args = parser.parse_args()

    # Validate paths
    if args.workspace and not os.path.exists(args.workspace):
        print(json.dumps({"success": False, "error": f"Workspace not found: {args.workspace}"}))
        return 1

    if args.project and not os.path.exists(args.project):
        print(json.dumps({"success": False, "error": f"Project not found: {args.project}"}))
        return 1

    # Find simulator
    simulator_id, error = find_simulator(
        name=args.simulator_name,
        udid=args.simulator_id,
        use_latest_os=args.use_latest_os
    )

    if error:
        print(json.dumps({"success": False, "error": error}))
        return 1

    # Build xcodebuild command
    cmd = ["xcodebuild"]

    if args.workspace:
        cmd.extend(["-workspace", args.workspace])
    else:
        cmd.extend(["-project", args.project])

    cmd.extend([
        "-scheme", args.scheme,
        "-configuration", args.configuration,
        "-destination", f"id={simulator_id}",
        "-skipMacroValidation",
        "-skipPackagePluginValidation",
        "build"
    ])

    if args.derived_data:
        cmd.extend(["-derivedDataPath", args.derived_data])

    if args.extra_args:
        cmd.extend(args.extra_args.split(","))

    # Run build
    result = run_xcodebuild(cmd)

    if result["success"]:
        result["message"] = f"Build succeeded for simulator {simulator_id}"
        result["simulator_id"] = simulator_id
        result["scheme"] = args.scheme
        result["configuration"] = args.configuration

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
