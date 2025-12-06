#!/usr/bin/env python3
"""
Run Swift package tests.

Usage:
    ./swift-test.py --path /path/to/package
    ./swift-test.py --path /path/to/package --filter "MyTests.testSomething"

Options:
    --path PATH               Path to Swift package
    --filter PATTERN          Filter tests by pattern
    --enable-code-coverage    Enable code coverage
"""

import argparse
import json
import subprocess
import sys
import os
import re


def main():
    parser = argparse.ArgumentParser(description="Run Swift package tests")
    parser.add_argument("--path", default=".", help="Path to Swift package")
    parser.add_argument("--filter", help="Filter tests by pattern")
    parser.add_argument("--enable-code-coverage", action="store_true", help="Enable code coverage")

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
    cmd = ["swift", "test", "--package-path", package_path]

    if args.filter:
        cmd.extend(["--filter", args.filter])

    if args.enable_code_coverage:
        cmd.append("--enable-code-coverage")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1200
        )

        output = result.stdout + result.stderr

        # Parse test results
        tests_passed = []
        tests_failed = []

        for line in output.split("\n"):
            # Swift test output format: "Test Case 'TestClass.testMethod' passed"
            if "passed" in line.lower() and "Test Case" in line:
                match = re.search(r"Test Case '([^']+)'", line)
                if match:
                    tests_passed.append(match.group(1))
            elif "failed" in line.lower() and "Test Case" in line:
                match = re.search(r"Test Case '([^']+)'", line)
                if match:
                    tests_failed.append(match.group(1))

        success = result.returncode == 0 and len(tests_failed) == 0

        response = {
            "success": success,
            "tests_passed": len(tests_passed),
            "tests_failed": len(tests_failed),
            "passed_tests": tests_passed[:50],
            "failed_tests": tests_failed
        }

        if success:
            response["message"] = f"All {len(tests_passed)} tests passed"
        else:
            response["message"] = f"{len(tests_failed)} test(s) failed"

        print(json.dumps(response, indent=2))
        return 0 if success else 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Tests timed out after 20 minutes"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
