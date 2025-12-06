#!/usr/bin/env python3
"""
Build and run a macOS application.

Usage:
    ./build-run-macos.py --workspace MyApp.xcworkspace --scheme MyApp
"""

import argparse
import json
import subprocess
import sys
import os


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


def main():
    parser = argparse.ArgumentParser(description="Build and run macOS app")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Build scheme")
    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--arch", choices=["arm64", "x86_64"], help="Architecture")
    parser.add_argument("--derived-data", help="Derived data path")

    args = parser.parse_args()

    # Validate paths
    if args.workspace and not os.path.exists(args.workspace):
        print(json.dumps({"success": False, "error": f"Workspace not found: {args.workspace}"}))
        return 1

    if args.project and not os.path.exists(args.project):
        print(json.dumps({"success": False, "error": f"Project not found: {args.project}"}))
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
        "-destination", "platform=macOS",
        "-skipMacroValidation",
        "-skipPackagePluginValidation",
        "build"
    ])

    if args.arch:
        cmd.extend(["-arch", args.arch])

    if args.derived_data:
        cmd.extend(["-derivedDataPath", args.derived_data])

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

    # Get app path
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

    # Launch
    try:
        subprocess.run(["open", app_path], capture_output=True, timeout=10)

        print(json.dumps({
            "success": True,
            "message": f"Built and launched {args.scheme}",
            "app_path": app_path
        }, indent=2))
        return 0

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Build succeeded but launch failed: {e}"
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
