#!/usr/bin/env python3
"""
Stop a running app on a connected physical device.

Usage:
    stop-app-device.py --device-id UDID --app /path/to/MyApp.app

Arguments:
    --device-id UDID    Device UDID (from list-devices.py)
    --app PATH          Path to .app bundle to stop

Output:
    JSON with termination status
"""

import argparse
import json
import subprocess
import sys
import tempfile
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


def get_app_name_for_bundle_id(device_id, bundle_id):
    """Get the app name for a bundle ID by querying installed apps."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        result = subprocess.run(
            ["xcrun", "devicectl", "device", "info", "apps",
             "--device", device_id, "--json-output", tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(tmp_path):
            try:
                with open(tmp_path) as f:
                    data = json.load(f)
                apps = data.get("result", {}).get("apps", [])
                for app in apps:
                    if app.get("bundleIdentifier") == bundle_id:
                        return app.get("name")
            except (json.JSONDecodeError, IOError):
                pass
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        return None
    except Exception:
        return None


def find_app_pid(device_id, app_name):
    """Find the PID of a running app by its app name."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        result = subprocess.run(
            ["xcrun", "devicectl", "device", "info", "processes",
             "--device", device_id, "--json-output", tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(tmp_path):
            try:
                with open(tmp_path) as f:
                    data = json.load(f)
                processes = data.get("result", {}).get("runningProcesses", [])
                app_name_lower = app_name.lower()

                for proc in processes:
                    exe = proc.get("executable", "").lower()
                    # Match by app name in .app bundle path
                    # e.g., /path/to/SurfTracker.app/SurfTracker
                    if f"/{app_name_lower}.app/" in exe or exe.endswith(f"/{app_name_lower}"):
                        return proc.get("processIdentifier")
            except (json.JSONDecodeError, IOError):
                pass
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        return None
    except Exception:
        return None


def stop_app(device_id, bundle_id):
    """Stop app using devicectl (Xcode 15+)."""
    try:
        # First, get the app name for this bundle ID
        app_name = get_app_name_for_bundle_id(device_id, bundle_id)

        if app_name is None:
            return False, f"App with bundle ID '{bundle_id}' is not installed on this device"

        # Find the PID for the app
        pid = find_app_pid(device_id, app_name)

        if pid is None:
            return True, "App was not running"

        # Terminate using the PID
        result = subprocess.run(
            ["xcrun", "devicectl", "device", "process", "terminate",
             "--device", device_id, "--pid", str(pid)],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return True, f"App '{app_name}' terminated successfully (PID {pid})"
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

    # Extract bundle ID from app
    bundle_id = get_bundle_id(app_path)
    if not bundle_id:
        print(json.dumps({
            "success": False,
            "error": "Could not extract bundle identifier from app",
            "app_path": app_path
        }))
        sys.exit(1)

    success, message = stop_app(device_id, bundle_id)

    if success:
        print(json.dumps({
            "success": True,
            "message": message,
            "device_id": device_id,
            "app_path": app_path,
            "bundle_id": bundle_id
        }))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "device_id": device_id,
            "app_path": app_path,
            "bundle_id": bundle_id,
            "hints": [
                "Ensure the app is running on the device",
                "Check that the device is connected"
            ]
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
