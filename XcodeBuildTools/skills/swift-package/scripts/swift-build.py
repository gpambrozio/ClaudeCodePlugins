#!/usr/bin/env python3
"""
Build a Swift package.

Usage:
    ./swift-build.py --path /path/to/package
    ./swift-build.py --path /path/to/package --configuration release

Options:
    --path PATH            Path to Swift package (default: current directory)
    --configuration CFG    Build mode (debug or release)
    --target TARGET        Specific target to build
    --arch ARCH            Architecture (arm64 or x86_64)
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Build Swift package")
    parser.add_argument("--path", default=".", help="Path to Swift package")
    parser.add_argument("--configuration", choices=["debug", "release"], default="debug", help="Build configuration")
    parser.add_argument("--target", help="Specific target to build")
    parser.add_argument("--arch", choices=["arm64", "x86_64"], help="Architecture")

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

    # Build command
    cmd = ["swift", "build", "--package-path", package_path]

    if args.configuration == "release":
        cmd.extend(["-c", "release"])

    if args.target:
        cmd.extend(["--target", args.target])

    if args.arch:
        cmd.extend(["--arch", args.arch])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        # Parse output for errors and warnings
        errors = []
        warnings = []

        for line in result.stdout.split("\n") + result.stderr.split("\n"):
            if ": error:" in line:
                errors.append(line.strip())
            elif ": warning:" in line:
                warnings.append(line.strip())

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Build succeeded",
                "configuration": args.configuration,
                "target": args.target,
                "warning_count": len(warnings),
                "warnings": warnings[:20]
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": "Build failed",
                "error_count": len(errors),
                "errors": errors[:20],
                "warnings": warnings[:20]
            }, indent=2))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Build timed out after 10 minutes"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
