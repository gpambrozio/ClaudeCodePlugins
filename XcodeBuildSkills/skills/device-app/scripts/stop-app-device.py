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
import tempfile
import os


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
