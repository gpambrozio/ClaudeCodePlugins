#!/usr/bin/env python3
"""
Build a Swift Package using `swift build`.

Usage:
    swift-package-build.py --package-path /path/to/package [options]

Arguments:
    --package-path PATH    Path to the Swift package root (required)
    --target NAME          Optional target to build
    --configuration CFG    Build configuration: debug (default) or release
    --arch ARCH            Target architecture (e.g., arm64, x86_64)
    --parse-as-library     Build as library instead of executable

Output:
    JSON with success status, build output or errors
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Build a Swift Package")
    parser.add_argument("--package-path", required=True, help="Path to Swift package root")
    parser.add_argument("--target", help="Specific target to build")
    parser.add_argument("--configuration", choices=["debug", "release"], default="debug")
    parser.add_argument("--arch", action="append", help="Target architecture (can specify multiple)")
    parser.add_argument("--parse-as-library", action="store_true", help="Add -parse-as-library flag")

    args = parser.parse_args()

    # Resolve to absolute path
    package_path = os.path.abspath(args.package_path)

    if not os.path.isdir(package_path):
        print(json.dumps({
            "success": False,
            "error": f"Package path does not exist: {package_path}"
        }))
        sys.exit(1)

    # Build command
    cmd = ["swift", "build", "--package-path", package_path]

    if args.configuration == "release":
        cmd.extend(["-c", "release"])

    if args.target:
        cmd.extend(["--target", args.target])

    if args.arch:
        for arch in args.arch:
            cmd.extend(["--arch", arch])

    if args.parse_as_library:
        cmd.extend(["-Xswiftc", "-parse-as-library"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=package_path
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Build completed successfully",
                "package_path": package_path,
                "configuration": args.configuration,
                "output": result.stdout.strip() if result.stdout.strip() else "Build succeeded with no output"
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": "Build failed",
                "stderr": result.stderr.strip(),
                "stdout": result.stdout.strip(),
                "command": " ".join(cmd)
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
