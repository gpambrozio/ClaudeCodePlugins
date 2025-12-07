#!/usr/bin/env python3
"""
Get the bundle identifier from an app bundle or Info.plist.

Usage:
    get-bundle-id.py --app /path/to/MyApp.app
    get-bundle-id.py --plist /path/to/Info.plist

Arguments:
    --app PATH      Path to .app bundle
    --plist PATH    Path to Info.plist file

Output:
    JSON with bundle identifier and other metadata
"""

import argparse
import json
import subprocess
import sys
import os
import plistlib


def read_plist(path):
    """Read a plist file and return its contents."""
    try:
        # Try using plutil first (handles binary and XML plists)
        result = subprocess.run(
            ["plutil", "-convert", "json", "-o", "-", path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass

    # Fallback to plistlib
    try:
        with open(path, 'rb') as f:
            return plistlib.load(f)
    except Exception as e:
        return None


def main():
    parser = argparse.ArgumentParser(description="Get bundle identifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--app", help="Path to .app bundle")
    group.add_argument("--plist", help="Path to Info.plist file")

    args = parser.parse_args()

    if args.app:
        app_path = os.path.abspath(args.app)

        if not os.path.isdir(app_path):
            print(json.dumps({
                "success": False,
                "error": f"App bundle does not exist: {app_path}"
            }))
            sys.exit(1)

        # Check for Info.plist in both iOS (flat) and macOS (Contents/) locations
        ios_plist_path = os.path.join(app_path, "Info.plist")
        macos_plist_path = os.path.join(app_path, "Contents", "Info.plist")

        if os.path.exists(ios_plist_path):
            plist_path = ios_plist_path
        elif os.path.exists(macos_plist_path):
            plist_path = macos_plist_path
        else:
            print(json.dumps({
                "success": False,
                "error": f"Info.plist not found in app bundle: {app_path}"
            }))
            sys.exit(1)
    else:
        plist_path = os.path.abspath(args.plist)
        app_path = None

        if not os.path.exists(plist_path):
            print(json.dumps({
                "success": False,
                "error": f"Info.plist not found: {plist_path}"
            }))
            sys.exit(1)

    plist_data = read_plist(plist_path)

    if plist_data is None:
        print(json.dumps({
            "success": False,
            "error": "Failed to parse Info.plist"
        }))
        sys.exit(1)

    bundle_id = plist_data.get("CFBundleIdentifier")
    if not bundle_id:
        print(json.dumps({
            "success": False,
            "error": "CFBundleIdentifier not found in Info.plist"
        }))
        sys.exit(1)

    result = {
        "success": True,
        "bundle_id": bundle_id,
        "bundle_name": plist_data.get("CFBundleName"),
        "bundle_display_name": plist_data.get("CFBundleDisplayName"),
        "bundle_version": plist_data.get("CFBundleVersion"),
        "bundle_short_version": plist_data.get("CFBundleShortVersionString"),
        "minimum_os_version": plist_data.get("MinimumOSVersion") or plist_data.get("LSMinimumSystemVersion"),
        "plist_path": plist_path
    }

    if app_path:
        result["app_path"] = app_path

    # Remove None values
    result = {k: v for k, v in result.items() if v is not None}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
