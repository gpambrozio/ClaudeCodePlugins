#!/usr/bin/env python3
"""
Clean Xcode build products using xcodebuild clean.

Usage:
    xcodebuild-clean.py --project /path/to/MyApp.xcodeproj --scheme MyApp
    xcodebuild-clean.py --workspace /path/to/MyApp.xcworkspace --scheme MyApp

Arguments:
    --project PATH        Path to .xcodeproj file (mutually exclusive with --workspace)
    --workspace PATH      Path to .xcworkspace file (mutually exclusive with --project)
    --scheme NAME         Scheme to clean (required for workspaces)
    --configuration CFG   Build configuration to clean (Debug, Release)
    --derived-data PATH   Path to derived data directory

Output:
    JSON with clean status
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Clean Xcode build products")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Path to .xcodeproj file")
    group.add_argument("--workspace", help="Path to .xcworkspace file")
    parser.add_argument("--scheme", help="Scheme to clean")
    parser.add_argument("--configuration", help="Build configuration (Debug, Release)")
    parser.add_argument("--derived-data", help="Derived data path")

    args = parser.parse_args()

    # Build command
    cmd = ["xcodebuild", "clean"]

    if args.project:
        path = os.path.abspath(args.project)
        cmd.extend(["-project", path])
        path_type = "project"
    else:
        path = os.path.abspath(args.workspace)
        cmd.extend(["-workspace", path])
        path_type = "workspace"
        if not args.scheme:
            print(json.dumps({
                "success": False,
                "error": "Scheme is required when using a workspace"
            }))
            sys.exit(1)

    if args.scheme:
        cmd.extend(["-scheme", args.scheme])

    if args.configuration:
        cmd.extend(["-configuration", args.configuration])

    if args.derived_data:
        cmd.extend(["-derivedDataPath", os.path.abspath(args.derived_data)])

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
            timeout=300
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Clean completed successfully",
                "path": path,
                "type": path_type,
                "scheme": args.scheme,
                "configuration": args.configuration or "all"
            }))
        else:
            # Parse error from output
            error = result.stderr.strip() or result.stdout.strip()
            print(json.dumps({
                "success": False,
                "error": error or "Clean failed",
                "path": path,
                "command": " ".join(cmd)
            }))
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "success": False,
            "error": "Clean timed out"
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
