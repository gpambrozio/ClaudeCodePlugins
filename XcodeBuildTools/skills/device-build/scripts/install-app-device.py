#!/usr/bin/env python3
"""
Install an app on a physical iOS device.

Usage:
    ./install-app-device.py --device-id <UDID> --app /path/to/MyApp.app

Options:
    --device-id UDID    Device UDID (required)
    --app PATH          Path to .app bundle (required)
"""

import argparse
import json
import subprocess
import sys
import os


def run_command(cmd, timeout=120):
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


def install_with_devicectl(device_id, app_path):
    """Install using devicectl (Xcode 15+)."""
    success, stdout, stderr = run_command([
        "xcrun", "devicectl", "device", "install", "app",
        "--device", device_id,
        app_path
    ])

    if success:
        return {"success": True, "message": f"App installed on device {device_id}"}
    else:
        return {"success": False, "error": stderr or stdout or "Installation failed"}


def install_with_ios_deploy(device_id, app_path):
    """Fallback: Install using ios-deploy if available."""
    success, stdout, stderr = run_command([
        "ios-deploy", "--id", device_id, "--bundle", app_path
    ])

    if success:
        return {"success": True, "message": f"App installed on device {device_id}"}
    else:
        return {"success": False, "error": stderr or stdout or "Installation failed"}


def main():
    parser = argparse.ArgumentParser(description="Install app on iOS device")
    parser.add_argument("--device-id", required=True, help="Device UDID")
    parser.add_argument("--app", required=True, help="Path to .app bundle")

    args = parser.parse_args()

    # Validate app path
    if not os.path.exists(args.app):
        print(json.dumps({"success": False, "error": f"App bundle not found: {args.app}"}))
        return 1

    if not args.app.endswith(".app"):
        print(json.dumps({"success": False, "error": "Path must point to a .app bundle"}))
        return 1

    # Try devicectl first
    result = install_with_devicectl(args.device_id, args.app)

    # Fallback to ios-deploy
    if not result["success"] and "not found" in result.get("error", "").lower():
        result = install_with_ios_deploy(args.device_id, args.app)

    result["device_id"] = args.device_id
    result["app_path"] = args.app

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
