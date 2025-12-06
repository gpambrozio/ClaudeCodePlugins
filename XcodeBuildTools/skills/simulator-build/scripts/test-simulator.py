#!/usr/bin/env python3
"""
Run tests on an iOS Simulator.

Usage:
    ./test-simulator.py --workspace MyApp.xcworkspace --scheme MyAppTests --simulator-name "iPhone 15"
    ./test-simulator.py --project MyApp.xcodeproj --scheme MyAppTests --simulator-id <UDID>

Options:
    --workspace PATH       Path to .xcworkspace file
    --project PATH         Path to .xcodeproj file
    --scheme NAME          Test scheme name (required)
    --simulator-name NAME  Simulator device name
    --simulator-id UDID    Simulator UDID
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


def find_simulator(name=None, udid=None, use_latest_os=False):
    """Find a simulator by name or UDID."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, "Failed to list simulators"

        data = json.loads(result.stdout)

        if udid:
            for runtime_devices in data.get("devices", {}).values():
                for device in runtime_devices:
                    if device.get("udid") == udid:
                        return device.get("udid"), None
            return None, f"Simulator with UDID {udid} not found"

        if name:
            matches = []
            runtimes = {r["identifier"]: r["name"] for r in data.get("runtimes", [])}

            for runtime_id, device_list in data.get("devices", {}).items():
                runtime_name = runtimes.get(runtime_id, "")
                for device in device_list:
                    if device.get("name") == name and device.get("isAvailable", False):
                        matches.append({
                            "udid": device.get("udid"),
                            "runtime": runtime_name,
                            "state": device.get("state")
                        })

            if not matches:
                return None, f"No simulator named '{name}' found"

            matches.sort(key=lambda x: x["runtime"], reverse=True)

            for m in matches:
                if m["state"] == "Booted":
                    return m["udid"], None

            return matches[0]["udid"], None

        return None, "Either --simulator-name or --simulator-id is required"

    except Exception as e:
        return None, str(e)


def run_tests(args, simulator_id, timeout=1200):
    """Run xcodebuild tests and return parsed result."""
    cmd = ["xcodebuild"]

    if args.workspace:
        cmd.extend(["-workspace", args.workspace])
    else:
        cmd.extend(["-project", args.project])

    cmd.extend([
        "-scheme", args.scheme,
        "-configuration", args.configuration,
        "-destination", f"id={simulator_id}",
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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

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

        return {
            "success": test_succeeded and len(tests_failed) == 0,
            "return_code": result.returncode,
            "tests_passed": len(tests_passed),
            "tests_failed": len(tests_failed),
            "passed_tests": tests_passed[:50],
            "failed_tests": tests_failed,
            "errors": errors[:10]
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Tests timed out after 20 minutes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Run tests on iOS Simulator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to .xcworkspace")
    group.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--scheme", required=True, help="Test scheme")

    sim_group = parser.add_mutually_exclusive_group(required=True)
    sim_group.add_argument("--simulator-name", help="Simulator device name")
    sim_group.add_argument("--simulator-id", help="Simulator UDID")

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

    # Find simulator
    simulator_id, error = find_simulator(
        name=args.simulator_name,
        udid=args.simulator_id
    )

    if error:
        print(json.dumps({"success": False, "error": error}))
        return 1

    # Run tests
    result = run_tests(args, simulator_id)

    result["scheme"] = args.scheme
    result["simulator_id"] = simulator_id

    if result["success"]:
        result["message"] = f"All {result['tests_passed']} tests passed"
    elif result.get("tests_failed", 0) > 0:
        result["message"] = f"{result['tests_failed']} test(s) failed"

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
