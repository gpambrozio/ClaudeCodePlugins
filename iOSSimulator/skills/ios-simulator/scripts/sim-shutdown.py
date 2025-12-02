#!/usr/bin/env python3
"""
Shutdown an iOS Simulator.

Usage:
    sim-shutdown.py --udid <udid>
    sim-shutdown.py --all

Options:
    --udid <udid>  Shutdown simulator by UDID
    --all          Shutdown all running simulators

Output:
    JSON object with success status
"""

import json
import sys
import argparse

from sim_utils import run_simctl, handle_simctl_result


def shutdown_simulator(udid):
    """Shutdown a simulator by UDID."""
    success, stdout, stderr = run_simctl('shutdown', udid)
    return success, stderr


def shutdown_all():
    """Shutdown all running simulators."""
    success, stdout, stderr = run_simctl('shutdown', 'all')
    return success, stderr


def main():
    parser = argparse.ArgumentParser(description='Shutdown iOS Simulator(s)')
    parser.add_argument('--udid', help='Simulator UDID to shutdown')
    parser.add_argument('--all', action='store_true', help='Shutdown all simulators')
    args = parser.parse_args()

    if not args.udid and not args.all:
        print(json.dumps({
            'success': False,
            'error': 'Either --udid or --all is required'
        }))
        sys.exit(1)

    if args.all:
        success, error = shutdown_all()
        if success:
            print(json.dumps({
                'success': True,
                'message': 'All simulators shutdown'
            }))
        else:
            _, response = handle_simctl_result(
                success, error, operation='shutdown all'
            )
            print(json.dumps(response))
            sys.exit(1)
        return

    success, error = shutdown_simulator(args.udid)

    if not success:
        actual_success, response = handle_simctl_result(
            success, error, operation='shutdown',
            context={'udid': args.udid}
        )

        if actual_success:
            # Non-error condition (already shutdown)
            response['udid'] = args.udid
            print(json.dumps(response))
            return

        print(json.dumps(response))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': 'Simulator shutdown successfully',
        'udid': args.udid
    }))


if __name__ == '__main__':
    main()
