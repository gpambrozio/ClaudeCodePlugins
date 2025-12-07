#!/usr/bin/env python3
"""
Install an app on a connected physical device.

Usage:
    install-app-device.py --device-id UDID --app /path/to/MyApp.app

Arguments:
    --device-id UDID    Device UDID (from list-devices.py)
    --app PATH          Path to .app bundle to install

Output:
    JSON with installation status
"""

import argparse
import json
import subprocess
import sys
import os


def install_app(device_id, app_path):
    """Install app using devicectl (Xcode 15+)."""
    try:
        result = subprocess.run(
            ["xcrun", "devicectl", "device", "install", "app",
             "--device", device_id, app_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for large apps
        )

        if result.returncode == 0:
            return True, "App installed successfully"
        else:
            return False, result.stderr.strip() or "Installation failed"

    except subprocess.TimeoutExpired:
        return False, "Installation timed out"
    except Exception as e:
        return False, str(e)


def install_app_legacy(device_id, app_path):
    """Fallback: Install app using ios-deploy if available."""
    try:
        result = subprocess.run(
            ["ios-deploy", "--id", device_id, "--bundle", app_path, "--no-wifi"],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            return True, "App installed successfully (via ios-deploy)"
        else:
            return False, result.stderr.strip() or "Installation failed"

    except FileNotFoundError:
        return False, "ios-deploy not found. Install with: brew install ios-deploy"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Install app on a physical device")
    parser.add_argument("--device-id", required=True, help="Device UDID")
    parser.add_argument("--app", required=True, help="Path to .app bundle")

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

    # Try devicectl first
    success, message = install_app(device_id, app_path)

    if not success and "not found" in message.lower():
        # Try ios-deploy as fallback
        success, message = install_app_legacy(device_id, app_path)

    if success:
        print(json.dumps({
            "success": True,
            "message": message,
            "device_id": device_id,
            "app_path": app_path,
            "next_steps": [
                "Use launch-app-device.py to launch the app",
                "Or manually tap the app icon on the device"
            ]
        }))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "device_id": device_id,
            "app_path": app_path,
            "hints": [
                "Ensure the device is connected and trusted",
                "Check that the app is signed for this device",
                "Verify Developer Mode is enabled on iOS 16+ devices"
            ]
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
