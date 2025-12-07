#!/usr/bin/env python3
"""
List schemes for an Xcode project or workspace.

Usage:
    list-schemes.py --project /path/to/MyApp.xcodeproj
    list-schemes.py --workspace /path/to/MyApp.xcworkspace

Arguments:
    --project PATH      Path to .xcodeproj file (mutually exclusive with --workspace)
    --workspace PATH    Path to .xcworkspace file (mutually exclusive with --project)

Output:
    JSON with list of available schemes
"""

import argparse
import json
import subprocess
import sys
import os
import re


def list_schemes(path, is_workspace=False):
    """List schemes using xcodebuild -list."""
    cmd = ["xcodebuild", "-list"]

    if is_workspace:
        cmd.extend(["-workspace", path])
    else:
        cmd.extend(["-project", path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return None, result.stderr.strip()

        # Parse schemes from output
        output = result.stdout
        schemes = []
        in_schemes = False

        for line in output.split('\n'):
            line = line.strip()

            if line == 'Schemes:':
                in_schemes = True
                continue

            if in_schemes:
                if line and not line.endswith(':'):
                    schemes.append(line)
                elif line.endswith(':') and line != 'Schemes:':
                    # Reached another section
                    break

        return schemes, None

    except subprocess.TimeoutExpired:
        return None, "Command timed out"
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="List Xcode schemes")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Path to .xcodeproj file")
    group.add_argument("--workspace", help="Path to .xcworkspace file")

    args = parser.parse_args()

    if args.project:
        path = os.path.abspath(args.project)
        is_workspace = False
        path_type = "project"
    else:
        path = os.path.abspath(args.workspace)
        is_workspace = True
        path_type = "workspace"

    if not os.path.exists(path):
        print(json.dumps({
            "success": False,
            "error": f"Path does not exist: {path}"
        }))
        sys.exit(1)

    schemes, error = list_schemes(path, is_workspace)

    if error:
        print(json.dumps({
            "success": False,
            "error": error,
            "path": path,
            "type": path_type
        }))
        sys.exit(1)

    print(json.dumps({
        "success": True,
        "path": path,
        "type": path_type,
        "schemes": schemes,
        "count": len(schemes)
    }))


if __name__ == "__main__":
    main()
