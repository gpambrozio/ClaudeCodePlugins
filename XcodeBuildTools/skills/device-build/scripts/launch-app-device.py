#!/usr/bin/env python3
"""
Launch an app on a physical iOS device.

Usage:
    ./launch-app-device.py --device-id <UDID> --bundle-id com.example.myapp
    ./launch-app-device.py --device-id <UDID> --bundle-id com.example.myapp --wait-for-debugger

Options:
    --device-id UDID       Device UDID (required)
    --bundle-id ID         App bundle identifier (required)
    --wait-for-debugger    Wait for debugger to attach before running
"""

import argparse
import json
import subprocess
import sys


def run_command(cmd, timeout=60):
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


def launch_with_devicectl(device_id, bundle_id, wait_for_debugger=False):
    """Launch app using devicectl (Xcode 15+)."""
    cmd = [
        "xcrun", "devicectl", "device", "process", "launch",
        "--device", device_id,
        bundle_id
    ]

    if wait_for_debugger:
        cmd.insert(5, "--wait-for-debugger")

    success, stdout, stderr = run_command(cmd)

    if success:
        # Try to extract PID from output
        pid = None
        for line in stdout.split("\n"):
            if "pid:" in line.lower() or "process" in line.lower():
                import re
                match = re.search(r"\d+", line)
                if match:
                    pid = int(match.group())
                    break

        result = {
            "success": True,
            "message": f"Launched {bundle_id} on device",
            "bundle_id": bundle_id,
            "device_id": device_id
        }
        if pid:
            result["pid"] = pid
        return result
    else:
        return {"success": False, "error": stderr or stdout or "Launch failed"}


def main():
    parser = argparse.ArgumentParser(description="Launch app on iOS device")
    parser.add_argument("--device-id", required=True, help="Device UDID")
    parser.add_argument("--bundle-id", required=True, help="App bundle identifier")
    parser.add_argument("--wait-for-debugger", action="store_true", help="Wait for debugger")

    args = parser.parse_args()

    result = launch_with_devicectl(args.device_id, args.bundle_id, args.wait_for_debugger)

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
