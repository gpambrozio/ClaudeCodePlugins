#!/usr/bin/env python3
"""
Terminate an app on an iOS Simulator.

Usage:
    sim-terminate.py --bundle-id <bundle-id> [--udid <udid>]
    sim-terminate.py -b <bundle-id>

Options:
    --bundle-id, -b <id>  App bundle identifier
    --udid <udid>         Simulator UDID (uses booted if not specified)

Output:
    JSON object with success status
"""

import json
import sys
import argparse

from sim_utils import run_simctl, get_booted_simulator_udid


def terminate_app(udid, bundle_id):
    """Terminate an app on the simulator."""
    success, stdout, stderr = run_simctl('terminate', udid, bundle_id)
    return success, stderr


def main():
    parser = argparse.ArgumentParser(description='Terminate app on iOS Simulator')
    parser.add_argument('--bundle-id', '-b', required=True, help='App bundle identifier')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    args = parser.parse_args()

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

    # Terminate the app
    success, error = terminate_app(udid, args.bundle_id)

    if not success:
        error_msg = error.strip() if error else 'Failed to terminate app'
        print(json.dumps({
            'success': False,
            'error': error_msg,
            'bundle_id': args.bundle_id
        }))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': f'Terminated {args.bundle_id}',
        'bundle_id': args.bundle_id,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
