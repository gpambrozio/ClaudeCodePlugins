#!/usr/bin/env python3
"""
Run Xcode tests using xcodebuild test.

Usage:
    xcode-test.py --project /path/to/MyApp.xcodeproj --scheme MyAppTests --destination "platform=iOS Simulator,name=iPhone 15"
    xcode-test.py --workspace /path/to/MyApp.xcworkspace --scheme MyAppTests --simulator-name "iPhone 15"

Arguments:
    --project PATH          Path to .xcodeproj file
    --workspace PATH        Path to .xcworkspace file
    --scheme NAME           Scheme to test (required)
    --simulator-id UDID     Simulator UDID for iOS tests
    --simulator-name NAME   Simulator name for iOS tests
    --macos                 Run tests on macOS
    --configuration CFG     Build configuration (Debug, Release)
    --derived-data PATH     Custom derived data path
    --only-testing TEST     Run only specific test (e.g., "MyAppTests/TestClass/testMethod")
    --skip-testing TEST     Skip specific test

Output:
    JSON with test results
"""

import argparse
import json
import subprocess
import sys
import os
import re


def find_simulator_by_name(name):
    """Find simulator UDID by name."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "-j"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        devices = data.get("devices", {})

        for runtime, device_list in devices.items():
            for device in device_list:
                if name.lower() in device.get("name", "").lower():
                    return device["udid"]

        return None

    except Exception:
        return None


def parse_test_results(output):
    """Parse test results from xcodebuild output."""
    tests_passed = 0
    tests_failed = 0
    test_failures = []

    for line in output.split('\n'):
        if 'Test Case' in line and 'passed' in line:
            tests_passed += 1
        elif 'Test Case' in line and 'failed' in line:
            tests_failed += 1
            # Extract test name
            match = re.search(r"Test Case '-\[(.+?)\]'", line)
            if match:
                test_failures.append(match.group(1))

    return tests_passed, tests_failed, test_failures


def main():
    parser = argparse.ArgumentParser(description="Run Xcode tests")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Path to .xcodeproj file")
    group.add_argument("--workspace", help="Path to .xcworkspace file")

    parser.add_argument("--scheme", required=True, help="Scheme to test")

    dest_group = parser.add_mutually_exclusive_group()
    dest_group.add_argument("--simulator-id", help="Simulator UDID")
    dest_group.add_argument("--simulator-name", help="Simulator name")
    dest_group.add_argument("--macos", action="store_true", help="Run on macOS")

    parser.add_argument("--configuration", default="Debug", help="Build configuration")
    parser.add_argument("--derived-data", help="Derived data path")
    parser.add_argument("--only-testing", action="append", help="Run only specific test")
    parser.add_argument("--skip-testing", action="append", help="Skip specific test")

    args = parser.parse_args()

    # Build command
    cmd = ["xcodebuild", "test"]

    if args.project:
        path = os.path.abspath(args.project)
        cmd.extend(["-project", path])
    else:
        path = os.path.abspath(args.workspace)
        cmd.extend(["-workspace", path])

    cmd.extend(["-scheme", args.scheme])
    cmd.extend(["-configuration", args.configuration])

    # Add destination
    if args.macos:
        cmd.extend(["-destination", "platform=macOS"])
    elif args.simulator_id:
        cmd.extend(["-destination", f"id={args.simulator_id}"])
    elif args.simulator_name:
        sim_id = find_simulator_by_name(args.simulator_name)
        if sim_id:
            cmd.extend(["-destination", f"id={sim_id}"])
        else:
            print(json.dumps({
                "success": False,
                "error": f"Simulator not found: {args.simulator_name}"
            }))
            sys.exit(1)
    else:
        # Default to iOS Simulator
        cmd.extend(["-destination", "platform=iOS Simulator,name=iPhone 15"])

    if args.derived_data:
        cmd.extend(["-derivedDataPath", os.path.abspath(args.derived_data)])

    if args.only_testing:
        for test in args.only_testing:
            cmd.extend(["-only-testing", test])

    if args.skip_testing:
        for test in args.skip_testing:
            cmd.extend(["-skip-testing", test])

    # Skip macro validation
    cmd.extend(["-skipMacroValidation", "-skipPackagePluginValidation"])

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
            timeout=1800  # 30 minute timeout for tests
        )

        passed, failed, failures = parse_test_results(result.stdout)

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "All tests passed",
                "tests_passed": passed,
                "tests_failed": failed,
                "scheme": args.scheme
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": "Tests failed",
                "tests_passed": passed,
                "tests_failed": failed,
                "failures": failures[:20],  # Limit to 20 failures
                "stderr": result.stderr.strip()[:2000] if result.stderr else None
            }))
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "success": False,
            "error": "Tests timed out after 30 minutes"
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
