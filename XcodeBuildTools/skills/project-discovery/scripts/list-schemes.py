#!/usr/bin/env python3
"""
List available build schemes for an Xcode project/workspace.

Usage:
    ./list-schemes.py --workspace MyApp.xcworkspace
    ./list-schemes.py --project MyApp.xcodeproj
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="List Xcode schemes")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")

    args = parser.parse_args()

    # Validate path
    path = args.workspace or args.project
    if not os.path.exists(path):
        print(json.dumps({"success": False, "error": f"Not found: {path}"}))
        return 1

    # Build command
    cmd = ["xcodebuild", "-list", "-json"]

    if args.workspace:
        cmd.extend(["-workspace", args.workspace])
    else:
        cmd.extend(["-project", args.project])

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
                "error": result.stderr or "Failed to list schemes"
            }))
            return 1

        data = json.loads(result.stdout)

        # Extract schemes from workspace or project structure
        if "workspace" in data:
            schemes = data["workspace"].get("schemes", [])
            name = data["workspace"].get("name", "")
        elif "project" in data:
            schemes = data["project"].get("schemes", [])
            name = data["project"].get("name", "")
        else:
            schemes = []
            name = ""

        print(json.dumps({
            "success": True,
            "name": name,
            "count": len(schemes),
            "schemes": schemes
        }, indent=2))
        return 0

    except json.JSONDecodeError:
        # Fallback: parse text output
        try:
            result = subprocess.run(
                cmd[:-1],  # Remove -json flag
                capture_output=True,
                text=True,
                timeout=60
            )

            schemes = []
            in_schemes = False
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line == "Schemes:":
                    in_schemes = True
                elif in_schemes and line:
                    if line.startswith("If no"):
                        break
                    schemes.append(line)

            print(json.dumps({
                "success": True,
                "count": len(schemes),
                "schemes": schemes
            }, indent=2))
            return 0

        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Command timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
