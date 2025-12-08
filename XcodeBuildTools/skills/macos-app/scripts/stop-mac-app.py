#!/usr/bin/env python3
"""
Stop a running macOS application.

Usage:
    stop-mac-app.py --bundle-id com.example.MyApp
    stop-mac-app.py --app-name "MyApp"

Arguments:
    --bundle-id BUNDLE    Bundle identifier of the app to stop
    --app-name NAME       Name of the app to stop (as shown in Activity Monitor)
    --force               Force quit the app (SIGKILL)

Output:
    JSON with termination status
"""

import argparse
import json
import subprocess
import sys


def stop_by_bundle_id(bundle_id, force=False):
    """Stop app by bundle identifier using osascript."""
    script = f'''
    tell application id "{bundle_id}"
        quit
    end tell
    '''

    if force:
        # Use pkill for force quit
        try:
            result = subprocess.run(
                ["pkill", "-9", "-f", bundle_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, "App force quit"
            elif result.returncode == 1:
                return True, "App was not running"
            else:
                return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return True, "App quit successfully"
        else:
            error = result.stderr.strip()
            if "not running" in error.lower():
                return True, "App was not running"
            return False, error or "Failed to quit app"

    except subprocess.TimeoutExpired:
        return False, "Quit timed out. Try using --force"
    except Exception as e:
        return False, str(e)


def stop_by_name(app_name, force=False):
    """Stop app by name using killall."""
    signal = "-9" if force else "-TERM"

    try:
        result = subprocess.run(
            ["killall", signal, app_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return True, "App terminated"
        elif result.returncode == 1:
            return True, "App was not running"
        else:
            return False, result.stderr.strip()

    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Stop a macOS application")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bundle-id", help="Bundle identifier of the app")
    group.add_argument("--app-name", help="Name of the app")
    parser.add_argument("--force", action="store_true", help="Force quit the app")

    args = parser.parse_args()

    if args.bundle_id:
        success, message = stop_by_bundle_id(args.bundle_id, args.force)
        identifier = args.bundle_id
    else:
        success, message = stop_by_name(args.app_name, args.force)
        identifier = args.app_name

    if success:
        print(json.dumps({
            "success": True,
            "message": message,
            "identifier": identifier
        }))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "identifier": identifier,
            "hint": "Try using --force to force quit"
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
