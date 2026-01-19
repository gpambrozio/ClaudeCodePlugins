#!/usr/bin/env python3
"""
Launch an app on a connected physical device.

Usage:
    launch-app-device.py --device-id UDID --app /path/to/MyApp.app

Arguments:
    --device-id UDID    Device UDID (from list-devices.py)
    --app PATH          Path to .app bundle to launch
    --args ARGS         Optional arguments to pass to the app

Output:
    JSON with launch status
"""

import argparse
import json
import subprocess
import sys
import os


def get_bundle_id(app_path):
    """Extract bundle identifier from app's Info.plist."""
    plist_path = os.path.join(app_path, "Info.plist")
    try:
        result = subprocess.run(
            ["/usr/libexec/PlistBuddy", "-c", "Print :CFBundleIdentifier", plist_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


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
    parser.add_argument("--app", required=True, help="Path to .app bundle")
    parser.add_argument("--args", nargs="*", help="Arguments to pass to the app")

    args = parser.parse_args()

    device_id = args.device_id
    app_path = os.path.abspath(args.app)

    # Validate app path
    if not os.path.isdir(app_path):
        print(json.dumps({
            "success": False,
            "error": f"App bundle not found: {app_path}"
        }))
        sys.exit(1)

    if not app_path.endswith('.app'):
        print(json.dumps({
            "success": False,
            "error": "Path must be a .app bundle"
        }))
        sys.exit(1)

    # Extract bundle ID from app
    bundle_id = get_bundle_id(app_path)
    if not bundle_id:
        print(json.dumps({
            "success": False,
            "error": "Could not extract bundle identifier from app",
            "app_path": app_path
        }))
        sys.exit(1)

    success, message, pid = launch_app(device_id, bundle_id, args.args)

    if success:
        result = {
            "success": True,
            "message": message,
            "device_id": device_id,
            "app_path": app_path,
            "bundle_id": bundle_id
        }
        if pid:
            result["pid"] = pid
        print(json.dumps(result))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "device_id": device_id,
            "app_path": app_path,
            "bundle_id": bundle_id,
            "hints": [
                "Ensure the app is installed on the device",
                "Check that the device is connected"
            ]
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
