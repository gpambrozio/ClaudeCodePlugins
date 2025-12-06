#!/usr/bin/env python3
"""
Show xcodebuild build settings for a project/workspace and scheme.

Usage:
    show-build-settings.py --project /path/to/MyApp.xcodeproj --scheme MyApp
    show-build-settings.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp

Arguments:
    --project PATH      Path to .xcodeproj file (mutually exclusive with --workspace)
    --workspace PATH    Path to .xcworkspace file (mutually exclusive with --project)
    --scheme NAME       Scheme name (required)
    --configuration CFG Build configuration (Debug, Release, etc.)
    --key KEY           Filter to show only specific key

Output:
    JSON with build settings
"""

import argparse
import json
import subprocess
import sys
import os
import re


def parse_build_settings(output):
    """Parse xcodebuild -showBuildSettings output into a dictionary."""
    settings = {}
    current_target = None

    for line in output.split('\n'):
        # Check for target header
        if line.startswith('Build settings for action'):
            match = re.search(r'target "([^"]+)"', line)
            if match:
                current_target = match.group(1)
            continue

        # Parse setting lines (indented with spaces, KEY = VALUE format)
        if '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key:
                    settings[key] = value

    return settings


def main():
    parser = argparse.ArgumentParser(description="Show Xcode build settings")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Path to .xcodeproj file")
    group.add_argument("--workspace", help="Path to .xcworkspace file")
    parser.add_argument("--scheme", required=True, help="Scheme name")
    parser.add_argument("--configuration", help="Build configuration (Debug, Release)")
    parser.add_argument("--key", help="Show only this specific setting key")

    args = parser.parse_args()

    if args.project:
        path = os.path.abspath(args.project)
        path_type = "project"
        cmd = ["xcodebuild", "-showBuildSettings", "-project", path, "-scheme", args.scheme]
    else:
        path = os.path.abspath(args.workspace)
        path_type = "workspace"
        cmd = ["xcodebuild", "-showBuildSettings", "-workspace", path, "-scheme", args.scheme]

    if args.configuration:
        cmd.extend(["-configuration", args.configuration])

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
            timeout=120
        )

        if result.returncode != 0:
            print(json.dumps({
                "success": False,
                "error": result.stderr.strip() or "Failed to get build settings",
                "path": path,
                "scheme": args.scheme
            }))
            sys.exit(1)

        settings = parse_build_settings(result.stdout)

        # Filter by key if specified
        if args.key:
            if args.key in settings:
                settings = {args.key: settings[args.key]}
            else:
                print(json.dumps({
                    "success": False,
                    "error": f"Setting key not found: {args.key}",
                    "available_keys": list(settings.keys())[:20],
                    "note": "Showing first 20 available keys"
                }))
                sys.exit(1)

        # Highlight commonly used settings
        common_keys = [
            "PRODUCT_NAME", "PRODUCT_BUNDLE_IDENTIFIER", "PRODUCT_MODULE_NAME",
            "INFOPLIST_FILE", "BUILT_PRODUCTS_DIR", "TARGET_BUILD_DIR",
            "CONFIGURATION_BUILD_DIR", "SWIFT_VERSION", "IPHONEOS_DEPLOYMENT_TARGET",
            "MACOSX_DEPLOYMENT_TARGET", "SDKROOT", "ARCHS"
        ]

        common_settings = {k: settings.get(k) for k in common_keys if k in settings}

        print(json.dumps({
            "success": True,
            "path": path,
            "type": path_type,
            "scheme": args.scheme,
            "configuration": args.configuration or "Default",
            "common_settings": common_settings,
            "all_settings": settings,
            "settings_count": len(settings)
        }))

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "success": False,
            "error": "Command timed out"
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
