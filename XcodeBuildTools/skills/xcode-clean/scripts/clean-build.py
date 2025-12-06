#!/usr/bin/env python3
"""
Clean Xcode build products for a project/workspace.

Usage:
    ./clean-build.py --workspace MyApp.xcworkspace --scheme MyApp
    ./clean-build.py --project MyApp.xcodeproj --scheme MyApp

Options:
    --workspace PATH       Path to .xcworkspace file
    --project PATH         Path to .xcodeproj file
    --scheme NAME          Build scheme name (required)
    --configuration CFG    Build configuration (default: Debug)
    --platform PLATFORM    Target platform
"""

import argparse
import json
import subprocess
import sys
import os


PLATFORMS = {
    "ios": "iOS",
    "ios-simulator": "iOS Simulator",
    "macos": "macOS",
    "watchos": "watchOS",
    "watchos-simulator": "watchOS Simulator",
    "tvos": "tvOS",
    "tvos-simulator": "tvOS Simulator",
    "visionos": "visionOS",
    "visionos-simulator": "visionOS Simulator"
}


def main():
    parser = argparse.ArgumentParser(description="Clean Xcode build")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Build scheme")
    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--platform", choices=list(PLATFORMS.keys()), help="Target platform")

    args = parser.parse_args()

    # Validate path
    path = args.workspace or args.project
    if not os.path.exists(path):
        print(json.dumps({"success": False, "error": f"Not found: {path}"}))
        return 1

    # Build command
    cmd = ["xcodebuild", "clean"]

    if args.workspace:
        cmd.extend(["-workspace", args.workspace])
    else:
        cmd.extend(["-project", args.project])

    cmd.extend(["-scheme", args.scheme, "-configuration", args.configuration])

    if args.platform:
        platform = PLATFORMS[args.platform]
        if "simulator" in args.platform.lower():
            cmd.extend(["-destination", f"generic/platform={platform}"])
        else:
            cmd.extend(["-destination", f"generic/platform={platform}"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Build products cleaned",
                "scheme": args.scheme,
                "configuration": args.configuration
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Clean failed"
            }))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Clean timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
