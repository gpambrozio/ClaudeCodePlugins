#!/usr/bin/env python3
"""
Run tests for a macOS application.

Usage:
    ./test-macos.py --workspace MyApp.xcworkspace --scheme MyAppTests
"""

import argparse
import json
import subprocess
import sys
import os
import re


def main():
    parser = argparse.ArgumentParser(description="Run macOS tests")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Test scheme")
    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--only-testing", help="Run only these tests (comma-separated)")
    parser.add_argument("--skip-testing", help="Skip these tests (comma-separated)")
    parser.add_argument("--derived-data", help="Derived data path")

    args = parser.parse_args()

    # Validate paths
    if args.workspace and not os.path.exists(args.workspace):
        print(json.dumps({"success": False, "error": f"Workspace not found: {args.workspace}"}))
        return 1

    if args.project and not os.path.exists(args.project):
        print(json.dumps({"success": False, "error": f"Project not found: {args.project}"}))
        return 1

    # Build xcodebuild command
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
        "test"
    ])

    if args.derived_data:
        cmd.extend(["-derivedDataPath", args.derived_data])

    if args.only_testing:
        for test in args.only_testing.split(","):
            cmd.extend(["-only-testing", test.strip()])

    if args.skip_testing:
        for test in args.skip_testing.split(","):
            cmd.extend(["-skip-testing", test.strip()])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)

        output = result.stdout + result.stderr

        tests_passed = []
        tests_failed = []
        errors = []

        for line in output.split("\n"):
            if "Test Case" in line:
                if "passed" in line.lower():
                    match = re.search(r"Test Case '-\[(\S+) (\S+)\]' passed", line)
                    if match:
                        tests_passed.append(f"{match.group(1)}/{match.group(2)}")
                elif "failed" in line.lower():
                    match = re.search(r"Test Case '-\[(\S+) (\S+)\]' failed", line)
                    if match:
                        tests_failed.append(f"{match.group(1)}/{match.group(2)}")

            if ": error:" in line:
                errors.append(line.strip())

        test_succeeded = "** TEST SUCCEEDED **" in output or result.returncode == 0

        response = {
            "success": test_succeeded and len(tests_failed) == 0,
            "return_code": result.returncode,
            "tests_passed": len(tests_passed),
            "tests_failed": len(tests_failed),
            "passed_tests": tests_passed[:50],
            "failed_tests": tests_failed,
            "errors": errors[:10],
            "scheme": args.scheme
        }

        if response["success"]:
            response["message"] = f"All {response['tests_passed']} tests passed"
        elif tests_failed:
            response["message"] = f"{len(tests_failed)} test(s) failed"

        print(json.dumps(response, indent=2))
        return 0 if response["success"] else 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Tests timed out after 20 minutes"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
