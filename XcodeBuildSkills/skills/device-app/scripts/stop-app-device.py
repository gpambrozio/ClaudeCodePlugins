#!/usr/bin/env python3
"""
Stop a running app on a connected physical device.

Usage:
    stop-app-device.py --device-id UDID --bundle-id com.example.MyApp

Arguments:
    --device-id UDID      Device UDID (from list-devices.py)
    --bundle-id BUNDLE    Bundle identifier of the app to stop

Output:
    JSON with termination status
"""

import argparse
import json
import subprocess
import sys


def stop_app(device_id, bundle_id):
    """Stop app using devicectl (Xcode 15+)."""
    try:
        result = subprocess.run(
            ["xcrun", "devicectl", "device", "process", "terminate",
             "--device", device_id, "--pid", bundle_id],
            capture_output=True,
            text=True,
            timeout=30
        )

        # devicectl might use different syntax, try alternative
        if result.returncode != 0:
            # Try with bundle ID directly
            result = subprocess.run(
                ["xcrun", "devicectl", "device", "process", "terminate",
                 "--device", device_id, bundle_id],
                capture_output=True,
                text=True,
                timeout=30
            )

        if result.returncode == 0:
            return True, "App terminated successfully"
        else:
            error = result.stderr.strip() or result.stdout.strip()
            # Check if app wasn't running
            if "not running" in error.lower() or "no process" in error.lower():
                return True, "App was not running"
            return False, error or "Termination failed"

    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Stop app on a physical device")
    parser.add_argument("--device-id", required=True, help="Device UDID")
    parser.add_argument("--bundle-id", required=True, help="Bundle identifier of the app")

    args = parser.parse_args()

    success, message = stop_app(args.device_id, args.bundle_id)

    if success:
        print(json.dumps({
            "success": True,
            "message": message,
            "device_id": args.device_id,
            "bundle_id": args.bundle_id
        }))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "device_id": args.device_id,
            "bundle_id": args.bundle_id,
            "hints": [
                "Ensure the app is running on the device",
                "Check that the device is connected",
                "Verify the bundle ID is correct"
            ]
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
