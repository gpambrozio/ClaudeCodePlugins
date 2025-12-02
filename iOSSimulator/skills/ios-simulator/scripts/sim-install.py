#!/usr/bin/env python3
"""
Install an app on an iOS Simulator.

Usage:
    sim-install.py --app <path> [--udid <udid>]

Options:
    --app <path>   Path to .app bundle or .ipa file
    --udid <udid>  Simulator UDID (uses booted if not specified)

Output:
    JSON object with success status and bundle info
"""

import json
import sys
import argparse
import os

from sim_utils import run_simctl, get_booted_simulator_udid, handle_simctl_result


def install_app(udid, app_path):
    """Install an app on the simulator."""
    success, stdout, stderr = run_simctl('install', udid, app_path)
    return success, stderr


def main():
    parser = argparse.ArgumentParser(description='Install app on iOS Simulator')
    parser.add_argument('--app', '-a', required=True, help='Path to .app or .ipa file')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    args = parser.parse_args()

    # Verify app exists
    if not os.path.exists(args.app):
        print(json.dumps({
            'success': False,
            'error': f'App not found: {args.app}'
        }))
        sys.exit(1)

    # Get UDID
    udid = args.udid
    if not udid:
        udid = get_booted_simulator_udid()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    # Install the app
    success, error = install_app(udid, args.app)

    if not success:
        _, response = handle_simctl_result(
            success, error, operation='install app',
            context={'app_path': args.app, 'udid': udid}
        )
        print(json.dumps(response))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': 'App installed successfully',
        'app_path': args.app,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
