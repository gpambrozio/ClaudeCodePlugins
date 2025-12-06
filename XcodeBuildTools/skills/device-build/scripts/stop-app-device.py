#!/usr/bin/env python3
"""
Stop/terminate an app on a physical iOS device.

Usage:
    ./stop-app-device.py --device-id <UDID> --bundle-id com.example.myapp

Options:
    --device-id UDID    Device UDID (required)
    --bundle-id ID      App bundle identifier (required)
"""

import argparse
import json
import subprocess
import sys


def run_command(cmd, timeout=30):
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def stop_with_devicectl(device_id, bundle_id):
    """Stop app using devicectl (Xcode 15+)."""
    # First, we need to find the PID of the running app
    success, stdout, stderr = run_command([
        "xcrun", "devicectl", "device", "info", "processes",
        "--device", device_id
    ])

    if not success:
        return {"success": False, "error": f"Failed to get process list: {stderr}"}

    # Find PID for bundle ID (this is a simplification - actual parsing may vary)
    pid = None
    for line in stdout.split("\n"):
        if bundle_id in line:
            import re
            match = re.search(r"^\s*(\d+)", line)
            if match:
                pid = match.group(1)
                break

    if pid:
        # Terminate the process
        success, stdout, stderr = run_command([
            "xcrun", "devicectl", "device", "process", "terminate",
            "--device", device_id,
            "--pid", pid
        ])

        if success:
            return {
                "success": True,
                "message": f"Terminated {bundle_id} (PID: {pid})",
                "bundle_id": bundle_id,
                "pid": int(pid)
            }
        else:
            return {"success": False, "error": stderr or "Failed to terminate"}
    else:
        # App might not be running - consider this success
        return {
            "success": True,
            "message": f"App {bundle_id} was not running",
            "bundle_id": bundle_id
        }


def main():
    parser = argparse.ArgumentParser(description="Stop app on iOS device")
    parser.add_argument("--device-id", required=True, help="Device UDID")
    parser.add_argument("--bundle-id", required=True, help="App bundle identifier")

    args = parser.parse_args()

    result = stop_with_devicectl(args.device_id, args.bundle_id)
    result["device_id"] = args.device_id

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
