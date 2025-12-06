#!/usr/bin/env python3
"""
Run tests on a physical iOS device.

Usage:
    ./test-device.py --workspace MyApp.xcworkspace --scheme MyAppTests --device-id <UDID>
    ./test-device.py --project MyApp.xcodeproj --scheme MyAppTests --device-id <UDID>

Options:
    --workspace PATH       Path to .xcworkspace file
    --project PATH         Path to .xcodeproj file
    --scheme NAME          Test scheme name (required)
    --device-id UDID       Device UDID (required)
    --configuration CFG    Build configuration (default: Debug)
    --only-testing TESTS   Run only specific tests (comma-separated)
    --skip-testing TESTS   Skip specific tests (comma-separated)
    --derived-data PATH    Custom derived data path
"""

import argparse
import json
import subprocess
import sys
import os
import re


def run_xcodebuild(args, timeout=1200):
    """Run xcodebuild test and return parsed result."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = result.stdout + result.stderr

        # Parse test results
        tests_passed = []
        tests_failed = []
        errors = []

        for line in output.split("\n"):
            # Match test results
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

        # Check for test success patterns
        test_succeeded = "** TEST SUCCEEDED **" in output or result.returncode == 0

        return {
            "success": test_succeeded and len(tests_failed) == 0,
            "return_code": result.returncode,
            "tests_passed": len(tests_passed),
            "tests_failed": len(tests_failed),
            "passed_tests": tests_passed[:50],  # Limit output
            "failed_tests": tests_failed,
            "errors": errors[:10]
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Tests timed out after 20 minutes"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Run tests on iOS device")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Test scheme")
    parser.add_argument("--device-id", required=True, help="Device UDID")
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
        "-destination", f"id={args.device_id}",
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

    # Run tests
    result = run_xcodebuild(cmd)

    result["scheme"] = args.scheme
    result["device_id"] = args.device_id

    if result["success"]:
        result["message"] = f"All {result['tests_passed']} tests passed"
    elif result.get("tests_failed", 0) > 0:
        result["message"] = f"{result['tests_failed']} test(s) failed"

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
