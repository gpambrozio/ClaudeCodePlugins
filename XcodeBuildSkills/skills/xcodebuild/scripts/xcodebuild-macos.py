#!/usr/bin/env python3
"""
Build a macOS app using xcodebuild.

Usage:
    xcodebuild-macos.py --project /path/to/MyApp.xcodeproj --scheme MyApp
    xcodebuild-macos.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp

Arguments:
    --project PATH          Path to .xcodeproj file
    --workspace PATH        Path to .xcworkspace file
    --scheme NAME           Scheme to build (required)
    --configuration CFG     Build configuration (Debug, Release)
    --arch ARCH             Architecture: arm64, x86_64
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


def main():
    parser = argparse.ArgumentParser(description="Build macOS app")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Path to .xcodeproj file")
    group.add_argument("--workspace", help="Path to .xcworkspace file")

    parser.add_argument("--scheme", required=True, help="Scheme to build")
    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--arch", choices=["arm64", "x86_64"], help="Target architecture")
    parser.add_argument("--derived-data", help="Derived data path")

    args = parser.parse_args()

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
    cmd.extend(["-destination", "platform=macOS"])

    if args.arch:
        cmd.extend(["-arch", args.arch])

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
                if '.app' in line and 'macos' in line.lower():
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
                "architecture": args.arch or "native",
                "app_path": app_path,
                "next_steps": [
                    "Use launch-mac-app.py to run the app",
                    "Or open the app directly with: open /path/to/MyApp.app"
                ]
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
