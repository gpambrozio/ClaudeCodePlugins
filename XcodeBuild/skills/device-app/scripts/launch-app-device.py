#!/usr/bin/env python3
"""
Launch an app on a connected physical device.

Usage:
    launch-app-device.py --device-id UDID --bundle-id com.example.MyApp

Arguments:
    --device-id UDID      Device UDID (from list-devices.py)
    --bundle-id BUNDLE    Bundle identifier of the app to launch
    --args ARGS           Optional arguments to pass to the app

Output:
    JSON with launch status
"""

import argparse
import json
import subprocess
import sys


def launch_app(device_id, bundle_id, args=None):
    """Launch app using devicectl (Xcode 15+)."""
    cmd = [
        "xcrun", "devicectl", "device", "process", "launch",
        "--device", device_id, bundle_id
    ]

    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            # Try to parse PID from output
            pid = None
            for line in result.stdout.split('\n'):
                if 'pid:' in line.lower():
                    try:
                        pid = int(line.split(':')[-1].strip())
                    except ValueError:
                        pass
            return True, "App launched successfully", pid
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return False, error or "Launch failed", None

    except subprocess.TimeoutExpired:
        return False, "Launch timed out", None
    except Exception as e:
        return False, str(e), None


def main():
    parser = argparse.ArgumentParser(description="Launch app on a physical device")
    parser.add_argument("--device-id", required=True, help="Device UDID")
    parser.add_argument("--bundle-id", required=True, help="Bundle identifier of the app")
    parser.add_argument("--args", nargs="*", help="Arguments to pass to the app")

    args = parser.parse_args()

    success, message, pid = launch_app(args.device_id, args.bundle_id, args.args)

    if success:
        result = {
            "success": True,
            "message": message,
            "device_id": args.device_id,
            "bundle_id": args.bundle_id
        }
        if pid:
            result["pid"] = pid
        print(json.dumps(result))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "device_id": args.device_id,
            "bundle_id": args.bundle_id,
            "hints": [
                "Ensure the app is installed on the device",
                "Check that the device is connected",
                "Verify the bundle ID is correct (use get-bundle-id.py)"
            ]
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
