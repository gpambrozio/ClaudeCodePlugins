#!/usr/bin/env python3
"""
Run tests for a Swift Package using `swift test`.

Usage:
    swift-package-test.py --package-path /path/to/package [options]

Arguments:
    --package-path PATH    Path to the Swift package root (required)
    --test-product NAME    Specific test product to run
    --filter PATTERN       Filter tests by name (regex pattern)
    --configuration CFG    Build configuration: debug (default) or release
    --parallel             Run tests in parallel (default: true)
    --no-parallel          Disable parallel test execution
    --show-codecov         Show code coverage
    --parse-as-library     Add -parse-as-library flag for @main support

Output:
    JSON with success status, test output or errors
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Run Swift Package tests")
    parser.add_argument("--package-path", required=True, help="Path to Swift package root")
    parser.add_argument("--test-product", help="Specific test product to run")
    parser.add_argument("--filter", help="Filter tests by name (regex pattern)")
    parser.add_argument("--configuration", choices=["debug", "release"], default="debug")
    parser.add_argument("--parallel", action="store_true", default=True, help="Run tests in parallel")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel execution")
    parser.add_argument("--show-codecov", action="store_true", help="Show code coverage")
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
    cmd = ["swift", "test", "--package-path", package_path]

    if args.configuration == "release":
        cmd.extend(["-c", "release"])

    if args.test_product:
        cmd.extend(["--test-product", args.test_product])

    if args.filter:
        cmd.extend(["--filter", args.filter])

    if args.no_parallel:
        cmd.append("--no-parallel")

    if args.show_codecov:
        cmd.append("--show-codecov")

    if args.parse_as_library:
        cmd.extend(["-Xswiftc", "-parse-as-library"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=package_path
        )

        output_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        stderr_lines = result.stderr.strip().split('\n') if result.stderr.strip() else []

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "All tests passed",
                "package_path": package_path,
                "output": result.stdout.strip()
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": "Tests failed",
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
