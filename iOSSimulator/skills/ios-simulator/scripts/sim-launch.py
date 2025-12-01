#!/usr/bin/env python3
"""
Launch an app on an iOS Simulator.

Usage:
    sim-launch.py --bundle-id <bundle-id> [--udid <udid>] [--args ...]
    sim-launch.py -b <bundle-id> [--wait]

Options:
    --bundle-id, -b <id>  App bundle identifier (e.g., com.apple.Preferences)
    --udid <udid>         Simulator UDID (uses booted if not specified)
    --wait                Wait for app to terminate and print output
    --args                Additional arguments to pass to the app

Common Bundle IDs:
    com.apple.Preferences        Settings
    com.apple.mobilesafari       Safari
    com.apple.MobileSMS          Messages
    com.apple.mobilephone        Phone
    com.apple.mobilecal          Calendar
    com.apple.mobilenotes        Notes
    com.apple.camera             Camera
    com.apple.Photos             Photos
    com.apple.AppStore           App Store
    com.apple.Maps               Maps

Output:
    JSON object with success status and process info
"""

import subprocess
import json
import sys
import argparse


def run_simctl(*args):
    """Run xcrun simctl command and return output."""
    cmd = ['xcrun', 'simctl'] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def get_booted_simulator():
    """Get the first booted simulator's UDID."""
    cmd = ['xcrun', 'simctl', 'list', '-j', 'devices']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    data = json.loads(result.stdout)
    for runtime, devices in data.get('devices', {}).items():
        for device in devices:
            if device.get('state') == 'Booted':
                return device.get('udid')
    return None


def launch_app(udid, bundle_id, wait=False, extra_args=None):
    """Launch an app on the simulator."""
    args = ['launch']
    if wait:
        args.append('--console-pty')
    args.extend([udid, bundle_id])
    if extra_args:
        args.extend(extra_args)

    success, stdout, stderr = run_simctl(*args)
    return success, stdout, stderr


def main():
    parser = argparse.ArgumentParser(description='Launch app on iOS Simulator')
    parser.add_argument('--bundle-id', '-b', required=True, help='App bundle identifier')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('--wait', action='store_true', help='Wait for app to terminate')
    parser.add_argument('args', nargs='*', help='Additional arguments for the app')
    parsed_args = parser.parse_args()

    # Get UDID
    udid = parsed_args.udid
    if not udid:
        udid = get_booted_simulator()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    # Launch the app
    success, stdout, stderr = launch_app(
        udid,
        parsed_args.bundle_id,
        parsed_args.wait,
        parsed_args.args if parsed_args.args else None
    )

    if not success:
        error_msg = stderr.strip() if stderr else 'Failed to launch app'

        # Provide helpful hints for common errors
        if 'Invalid bundle identifier' in error_msg:
            error_msg += '. The app may not be installed.'

        print(json.dumps({
            'success': False,
            'error': error_msg,
            'bundle_id': parsed_args.bundle_id
        }))
        sys.exit(1)

    # Parse PID from output if present (format: "com.app.id: 12345")
    pid = None
    if stdout:
        parts = stdout.strip().split(': ')
        if len(parts) >= 2 and parts[-1].isdigit():
            pid = int(parts[-1])

    result = {
        'success': True,
        'message': f'Launched {parsed_args.bundle_id}',
        'bundle_id': parsed_args.bundle_id,
        'udid': udid
    }
    if pid:
        result['pid'] = pid

    print(json.dumps(result))


if __name__ == '__main__':
    main()
