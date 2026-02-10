#!/usr/bin/env python3
"""
Delete iOS Simulator devices permanently.

Usage:
    sim-delete.py --udid <udid>
    sim-delete.py --name "iPhone 15"
    sim-delete.py --unavailable

Options:
    --udid <udid>       Delete simulator by UDID
    --name <name>       Delete simulator by name
    --unavailable       Delete all unavailable (stale) simulators
    --all               Delete ALL simulators (use with caution)

Output:
    JSON object with success status and details.

Notes:
    - This permanently removes the simulator and its data
    - Use sim-erase.py for a factory reset that preserves the device
    - The --unavailable option is useful for cleaning up after Xcode updates
"""

import json
import sys
import argparse

from sim_utils import run_simctl, find_simulator_by_name, handle_simctl_result


def main():
    parser = argparse.ArgumentParser(description='Delete iOS Simulator devices permanently')

    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--udid', help='Simulator UDID to delete')
    target.add_argument('--name', help='Simulator name to delete')
    target.add_argument('--unavailable', action='store_true',
                        help='Delete all unavailable (stale) simulators')
    target.add_argument('--all', action='store_true',
                        help='Delete ALL simulators')

    args = parser.parse_args()

    # Delete unavailable simulators
    if args.unavailable:
        success, stdout, stderr = run_simctl('delete', 'unavailable')
        if success:
            print(json.dumps({
                'success': True,
                'message': 'Deleted all unavailable simulators',
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Failed to delete unavailable simulators: {stderr.strip()}'
            }))
            sys.exit(1)
        return

    # Delete all simulators
    if args.all:
        success, stdout, stderr = run_simctl('delete', 'all')
        if success:
            print(json.dumps({
                'success': True,
                'message': 'Deleted all simulators',
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Failed to delete all simulators: {stderr.strip()}'
            }))
            sys.exit(1)
        return

    # Resolve UDID from name if needed
    udid = args.udid
    device_name = None
    if args.name:
        sim = find_simulator_by_name(args.name)
        if not sim:
            print(json.dumps({
                'success': False,
                'error': f"No simulator found with name '{args.name}'. Use sim-list.py to see available simulators."
            }))
            sys.exit(1)
        udid = sim['udid']
        device_name = sim['name']

    # Delete the device
    success, stdout, stderr = run_simctl('delete', udid)

    if not success:
        ok, response = handle_simctl_result(
            success, stderr, operation='delete simulator',
            context={'udid': udid}
        )
        if not ok:
            print(json.dumps(response))
            sys.exit(1)
        # handle_simctl_result may treat some "errors" as success
        print(json.dumps(response))
        return

    result = {
        'success': True,
        'message': f'Deleted simulator {device_name or udid}',
        'udid': udid,
    }
    if device_name:
        result['name'] = device_name

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
