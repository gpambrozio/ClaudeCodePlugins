#!/usr/bin/env python3
"""
Show build settings for an Xcode scheme.

Usage:
    ./show-build-settings.py --workspace MyApp.xcworkspace --scheme MyApp
    ./show-build-settings.py --project MyApp.xcodeproj --scheme MyApp --setting PRODUCT_BUNDLE_IDENTIFIER
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Show Xcode build settings")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Scheme name")
    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--setting", help="Specific setting to show")

    args = parser.parse_args()

    # Validate path
    path = args.workspace or args.project
    if not os.path.exists(path):
        print(json.dumps({"success": False, "error": f"Not found: {path}"}))
        return 1

    # Build command
    cmd = ["xcodebuild", "-showBuildSettings"]

    if args.workspace:
        cmd.extend(["-workspace", args.workspace])
    else:
        cmd.extend(["-project", args.project])

    cmd.extend(["-scheme", args.scheme, "-configuration", args.configuration])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Failed to get build settings"
            }))
            return 1

        # Parse build settings
        settings = {}
        for line in result.stdout.split("\n"):
            line = line.strip()
            if " = " in line:
                key, value = line.split(" = ", 1)
                key = key.strip()
                value = value.strip()
                settings[key] = value

        # Filter to specific setting if requested
        if args.setting:
            if args.setting in settings:
                print(json.dumps({
                    "success": True,
                    "setting": args.setting,
                    "value": settings[args.setting]
                }, indent=2))
            else:
                print(json.dumps({
                    "success": False,
                    "error": f"Setting '{args.setting}' not found"
                }))
                return 1
        else:
            # Return common useful settings
            common_settings = [
                "PRODUCT_NAME",
                "PRODUCT_BUNDLE_IDENTIFIER",
                "PRODUCT_MODULE_NAME",
                "BUILT_PRODUCTS_DIR",
                "TARGET_BUILD_DIR",
                "INFOPLIST_FILE",
                "SWIFT_VERSION",
                "IPHONEOS_DEPLOYMENT_TARGET",
                "MACOSX_DEPLOYMENT_TARGET",
                "SDKROOT",
                "CONFIGURATION",
                "PLATFORM_NAME"
            ]

            filtered = {k: settings.get(k) for k in common_settings if k in settings}

            print(json.dumps({
                "success": True,
                "scheme": args.scheme,
                "configuration": args.configuration,
                "settings": filtered,
                "all_settings_count": len(settings)
            }, indent=2))

        return 0

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Command timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
