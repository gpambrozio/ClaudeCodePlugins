#!/usr/bin/env python3
"""
Build an Xcode project/workspace for a physical iOS device.

Usage:
    ./build-device.py --workspace MyApp.xcworkspace --scheme MyApp --device-id <UDID>
    ./build-device.py --project MyApp.xcodeproj --scheme MyApp --device-id <UDID>

Options:
    --workspace PATH     Path to .xcworkspace file
    --project PATH       Path to .xcodeproj file
    --scheme NAME        Build scheme name (required)
    --device-id UDID     Device UDID (required)
    --configuration CFG  Build configuration (default: Debug)
    --derived-data PATH  Custom derived data path
    --extra-args ARGS    Additional xcodebuild arguments (comma-separated)
"""

import argparse
import json
import subprocess
import sys
import os


def run_xcodebuild(args, timeout=600):
    """Run xcodebuild and return parsed result."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # Parse output for errors and warnings
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
            "errors": errors[:20],  # Limit to first 20
            "warnings": warnings[:20],
            "error_count": len(errors),
            "warning_count": len(warnings)
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Build timed out after 10 minutes"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Build for iOS device")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Build scheme")
    parser.add_argument("--device-id", required=True, help="Device UDID")
    parser.add_argument("--configuration", default="Debug", help="Build configuration")
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

    # Build xcodebuild command
    cmd = ["xcodebuild"]

    if args.workspace:
        cmd.extend(["-workspace", args.workspace])
    else:
        cmd.extend(["-project", args.project])

    cmd.extend([
        "-scheme", args.scheme,
        "-configuration", args.configuration,
        "-destination", f"id={args.device_id}",
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
        result["message"] = f"Build succeeded for device {args.device_id}"
        result["scheme"] = args.scheme
        result["configuration"] = args.configuration

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
