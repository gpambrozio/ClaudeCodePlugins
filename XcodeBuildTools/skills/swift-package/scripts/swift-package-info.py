#!/usr/bin/env python3
"""
Show Swift package information.

Usage:
    ./swift-package-info.py --path /path/to/package
    ./swift-package-info.py --path /path/to/package --show-dependencies
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Show Swift package info")
    parser.add_argument("--path", default=".", help="Path to Swift package")
    parser.add_argument("--show-dependencies", action="store_true", help="Show dependencies")

    args = parser.parse_args()

    # Resolve and validate path
    package_path = os.path.abspath(args.path)
    package_swift = os.path.join(package_path, "Package.swift")

    if not os.path.exists(package_swift):
        print(json.dumps({
            "success": False,
            "error": f"No Package.swift found at {package_path}"
        }))
        return 1

    try:
        # Get package description
        result = subprocess.run(
            ["swift", "package", "describe", "--type", "json", "--package-path", package_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            # Fallback: try dump
            result = subprocess.run(
                ["swift", "package", "dump-package", "--package-path", package_path],
                capture_output=True,
                text=True,
                timeout=60
            )

        if result.returncode != 0:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Failed to get package info"
            }))
            return 1

        try:
            data = json.loads(result.stdout)

            response = {
                "success": True,
                "name": data.get("name"),
                "path": package_path
            }

            # Extract targets
            targets = data.get("targets", [])
            if targets:
                response["targets"] = [
                    {
                        "name": t.get("name"),
                        "type": t.get("type")
                    }
                    for t in targets
                ]

            # Extract products
            products = data.get("products", [])
            if products:
                response["products"] = [
                    {
                        "name": p.get("name"),
                        "type": list(p.get("type", {}).keys())[0] if isinstance(p.get("type"), dict) else p.get("type")
                    }
                    for p in products
                ]

            # Extract dependencies if requested
            if args.show_dependencies:
                deps = data.get("dependencies", [])
                if deps:
                    response["dependencies"] = [
                        {
                            "name": d.get("identity") or d.get("name"),
                            "url": d.get("url"),
                            "requirement": d.get("requirement")
                        }
                        for d in deps
                    ]

            print(json.dumps(response, indent=2))
            return 0

        except json.JSONDecodeError:
            # Return raw output if not JSON
            print(json.dumps({
                "success": True,
                "path": package_path,
                "description": result.stdout[:2000]
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
