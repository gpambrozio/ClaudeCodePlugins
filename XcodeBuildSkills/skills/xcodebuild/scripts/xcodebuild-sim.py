#!/usr/bin/env python3
"""
Build an iOS/tvOS/watchOS app for the simulator using xcodebuild.

Usage:
    xcodebuild-sim.py --project /path/to/MyApp.xcodeproj --scheme MyApp --simulator-id UDID
    xcodebuild-sim.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp --simulator-name "iPhone 15"

Arguments:
    --project PATH          Path to .xcodeproj file
    --workspace PATH        Path to .xcworkspace file
    --scheme NAME           Scheme to build (required)
    --simulator-id UDID     Simulator UDID to build for
    --simulator-name NAME   Simulator name (e.g., "iPhone 15")
    --configuration CFG     Build configuration (Debug, Release)
    --derived-data PATH     Custom derived data path

Output:
    JSON with build status and app path
"""

import argparse
import json
import subprocess
import sys
import os
import re


def find_simulator_by_name(name):
    """Find simulator UDID by name."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "-j"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        devices = data.get("devices", {})

        # Find matching simulator (prefer booted, then latest iOS)
        candidates = []
        for runtime, device_list in devices.items():
            for device in device_list:
                if name.lower() in device.get("name", "").lower():
                    candidates.append({
                        "udid": device["udid"],
                        "name": device["name"],
                        "runtime": runtime,
                        "state": device.get("state", "Unknown")
                    })

        if not candidates:
            return None

        # Prefer booted simulators
        booted = [c for c in candidates if c["state"] == "Booted"]
        if booted:
            return booted[0]["udid"]

        # Return first match
        return candidates[0]["udid"]

    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Build app for iOS simulator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Path to .xcodeproj file")
    group.add_argument("--workspace", help="Path to .xcworkspace file")

    parser.add_argument("--scheme", required=True, help="Scheme to build")

    sim_group = parser.add_mutually_exclusive_group()
    sim_group.add_argument("--simulator-id", help="Simulator UDID")
    sim_group.add_argument("--simulator-name", help="Simulator name")

    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--derived-data", help="Derived data path")

    args = parser.parse_args()

    # Resolve simulator
    simulator_id = args.simulator_id
    if args.simulator_name:
        simulator_id = find_simulator_by_name(args.simulator_name)
        if not simulator_id:
            print(json.dumps({
                "success": False,
                "error": f"Simulator not found: {args.simulator_name}",
                "hint": "Use 'xcrun simctl list devices' to see available simulators"
            }))
            sys.exit(1)

    # Build command
    cmd = ["xcodebuild", "build"]

    if args.project:
        path = os.path.abspath(args.project)
        cmd.extend(["-project", path])
        path_type = "project"
    else:
        path = os.path.abspath(args.workspace)
        cmd.extend(["-workspace", path])
        path_type = "workspace"

    cmd.extend(["-scheme", args.scheme])
    cmd.extend(["-configuration", args.configuration])

    # Add destination
    if simulator_id:
        cmd.extend(["-destination", f"id={simulator_id}"])
    else:
        cmd.extend(["-destination", "generic/platform=iOS Simulator"])

    if args.derived_data:
        cmd.extend(["-derivedDataPath", os.path.abspath(args.derived_data)])

    # Skip macro validation for faster builds
    cmd.extend(["-skipMacroValidation", "-skipPackagePluginValidation"])

    if not os.path.exists(path):
        print(json.dumps({
            "success": False,
            "error": f"Path does not exist: {path}"
        }))
        sys.exit(1)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            # Try to find built app path
            app_path = None
            for line in result.stdout.split('\n'):
                if '.app' in line and 'BUILD_DIR' not in line:
                    match = re.search(r'(/[^\s]+\.app)', line)
                    if match:
                        app_path = match.group(1)
                        break

            print(json.dumps({
                "success": True,
                "message": "Build completed successfully",
                "path": path,
                "type": path_type,
                "scheme": args.scheme,
                "configuration": args.configuration,
                "simulator_id": simulator_id,
                "app_path": app_path
            }))
        else:
            # Extract error message
            error_lines = []
            for line in result.stdout.split('\n') + result.stderr.split('\n'):
                if 'error:' in line.lower():
                    error_lines.append(line.strip())

            print(json.dumps({
                "success": False,
                "error": "Build failed",
                "errors": error_lines[:10] if error_lines else ["See build output for details"],
                "stderr": result.stderr.strip()[:1000] if result.stderr else None
            }))
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "success": False,
            "error": "Build timed out after 10 minutes"
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
