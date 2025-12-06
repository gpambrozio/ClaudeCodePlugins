#!/usr/bin/env python3
"""
Build and run an app on iOS Simulator.

Usage:
    ./build-run-simulator.py --workspace MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15"

This combines building, installing, and launching in one step.
"""

import argparse
import json
import subprocess
import sys
import os
import re


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
            return None, None, "Failed to list simulators"

        data = json.loads(result.stdout)

        if udid:
            for runtime_devices in data.get("devices", {}).values():
                for device in runtime_devices:
                    if device.get("udid") == udid:
                        return device.get("udid"), device.get("state"), None
            return None, None, f"Simulator with UDID {udid} not found"

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
                return None, None, f"No simulator named '{name}' found"

            matches.sort(key=lambda x: x["runtime"], reverse=True)

            if use_latest_os:
                return matches[0]["udid"], matches[0]["state"], None

            for m in matches:
                if m["state"] == "Booted":
                    return m["udid"], m["state"], None

            return matches[0]["udid"], matches[0]["state"], None

        return None, None, "Either --simulator-name or --simulator-id is required"

    except Exception as e:
        return None, None, str(e)


def boot_simulator(simulator_id):
    """Boot a simulator if not already booted."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "boot", simulator_id],
            capture_output=True,
            text=True,
            timeout=60
        )
        # It's OK if already booted
        return True, None
    except Exception as e:
        return False, str(e)


def get_app_path(workspace=None, project=None, scheme=None, configuration="Debug", derived_data=None):
    """Get the built app path from build settings."""
    cmd = ["xcodebuild", "-showBuildSettings"]

    if workspace:
        cmd.extend(["-workspace", workspace])
    else:
        cmd.extend(["-project", project])

    cmd.extend(["-scheme", scheme, "-configuration", configuration])

    if derived_data:
        cmd.extend(["-derivedDataPath", derived_data])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        built_products_dir = None
        product_name = None

        for line in result.stdout.split("\n"):
            if "BUILT_PRODUCTS_DIR = " in line:
                built_products_dir = line.split("=")[1].strip()
            elif "PRODUCT_NAME = " in line:
                product_name = line.split("=")[1].strip()

        if built_products_dir and product_name:
            return os.path.join(built_products_dir, f"{product_name}.app"), None

        return None, "Could not determine app path from build settings"

    except Exception as e:
        return None, str(e)


def get_bundle_id(app_path):
    """Get bundle ID from app's Info.plist."""
    plist_path = os.path.join(app_path, "Info.plist")
    try:
        result = subprocess.run(
            ["defaults", "read", plist_path, "CFBundleIdentifier"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip(), None
        return None, "Could not read bundle ID"
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Build and run on iOS Simulator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Build scheme")

    sim_group = parser.add_mutually_exclusive_group(required=True)
    sim_group.add_argument("--simulator-name", help="Simulator device name")
    sim_group.add_argument("--simulator-id", help="Simulator UDID")

    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--use-latest-os", action="store_true", help="Use latest OS")
    parser.add_argument("--derived-data", help="Derived data path")
    parser.add_argument("--extra-args", help="Extra xcodebuild args")

    args = parser.parse_args()

    # Validate paths
    if args.workspace and not os.path.exists(args.workspace):
        print(json.dumps({"success": False, "error": f"Workspace not found: {args.workspace}"}))
        return 1

    if args.project and not os.path.exists(args.project):
        print(json.dumps({"success": False, "error": f"Project not found: {args.project}"}))
        return 1

    # Find simulator
    simulator_id, state, error = find_simulator(
        name=args.simulator_name,
        udid=args.simulator_id,
        use_latest_os=args.use_latest_os
    )

    if error:
        print(json.dumps({"success": False, "error": error}))
        return 1

    # Boot if needed
    if state != "Booted":
        success, error = boot_simulator(simulator_id)
        if not success:
            print(json.dumps({"success": False, "error": f"Failed to boot simulator: {error}"}))
            return 1

    # Build
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

    try:
        build_result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if build_result.returncode != 0:
            errors = [l for l in build_result.stdout.split("\n") if ": error:" in l][:10]
            print(json.dumps({
                "success": False,
                "error": "Build failed",
                "errors": errors
            }))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Build timed out"}))
        return 1

    # Get app path and bundle ID
    app_path, error = get_app_path(
        workspace=args.workspace,
        project=args.project,
        scheme=args.scheme,
        configuration=args.configuration,
        derived_data=args.derived_data
    )

    if error:
        print(json.dumps({"success": False, "error": f"Build succeeded but could not find app: {error}"}))
        return 1

    bundle_id, error = get_bundle_id(app_path)
    if error:
        bundle_id = "unknown"

    # Install and launch
    try:
        subprocess.run(
            ["xcrun", "simctl", "install", simulator_id, app_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        subprocess.run(
            ["xcrun", "simctl", "launch", simulator_id, bundle_id],
            capture_output=True,
            text=True,
            timeout=30
        )

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Build succeeded but launch failed: {e}"
        }))
        return 1

    print(json.dumps({
        "success": True,
        "message": f"Built and launched {args.scheme} on simulator",
        "simulator_id": simulator_id,
        "bundle_id": bundle_id,
        "app_path": app_path
    }, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
