#!/usr/bin/env python3
"""
Get bundle identifier for an app.

Usage:
    ./get-bundle-id.py --workspace MyApp.xcworkspace --scheme MyApp
    ./get-bundle-id.py --app /path/to/MyApp.app
"""

import argparse
import json
import subprocess
import sys
import os


def get_bundle_id_from_app(app_path):
    """Get bundle ID from an app's Info.plist."""
    plist_path = os.path.join(app_path, "Info.plist")

    if not os.path.exists(plist_path):
        return None, f"Info.plist not found in {app_path}"

    try:
        result = subprocess.run(
            ["defaults", "read", plist_path, "CFBundleIdentifier"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return result.stdout.strip(), None
        else:
            return None, "Could not read CFBundleIdentifier"

    except Exception as e:
        return None, str(e)


def get_bundle_id_from_build_settings(workspace=None, project=None, scheme=None, configuration="Debug"):
    """Get bundle ID from build settings."""
    cmd = ["xcodebuild", "-showBuildSettings"]

    if workspace:
        cmd.extend(["-workspace", workspace])
    else:
        cmd.extend(["-project", project])

    cmd.extend(["-scheme", scheme, "-configuration", configuration])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        for line in result.stdout.split("\n"):
            if "PRODUCT_BUNDLE_IDENTIFIER = " in line:
                return line.split("=")[1].strip(), None

        return None, "PRODUCT_BUNDLE_IDENTIFIER not found in build settings"

    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Get app bundle identifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    group.add_argument("--app", help="Path to .app bundle")
    parser.add_argument("--scheme", help="Scheme name (required with --workspace/--project)")
    parser.add_argument("--configuration", default="Debug", help="Build configuration")

    args = parser.parse_args()

    if args.app:
        if not os.path.exists(args.app):
            print(json.dumps({"success": False, "error": f"App not found: {args.app}"}))
            return 1

        bundle_id, error = get_bundle_id_from_app(args.app)

        if error:
            print(json.dumps({"success": False, "error": error}))
            return 1

        print(json.dumps({
            "success": True,
            "bundle_id": bundle_id,
            "source": "app",
            "app_path": args.app
        }, indent=2))
        return 0

    else:
        if not args.scheme:
            print(json.dumps({"success": False, "error": "--scheme is required with --workspace/--project"}))
            return 1

        path = args.workspace or args.project
        if not os.path.exists(path):
            print(json.dumps({"success": False, "error": f"Not found: {path}"}))
            return 1

        bundle_id, error = get_bundle_id_from_build_settings(
            workspace=args.workspace,
            project=args.project,
            scheme=args.scheme,
            configuration=args.configuration
        )

        if error:
            print(json.dumps({"success": False, "error": error}))
            return 1

        print(json.dumps({
            "success": True,
            "bundle_id": bundle_id,
            "source": "build_settings",
            "scheme": args.scheme
        }, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())
