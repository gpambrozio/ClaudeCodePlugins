#!/usr/bin/env python3
"""
Factory reset an iOS Simulator (erase all content and settings).

Preserves the device UUID, which is faster than deleting and recreating.

Usage:
    sim-erase.py --udid <udid>
    sim-erase.py --name "iPhone 15"
    sim-erase.py --all

Options:
    --udid <udid>       Erase simulator by UDID
    --name <name>       Erase simulator by name
    --all               Erase all simulators

Output:
    JSON object with success status and details.

Notes:
    - The simulator must be shut down before erasing
    - This removes all apps, data, and settings but keeps the device
    - Faster than delete + create since the UUID is preserved
    - Use sim-delete.py to permanently remove a simulator
"""

import json
import sys
import argparse

from sim_utils import run_simctl, get_booted_simulator_udid, find_simulator_by_name, handle_simctl_result


def main():
    parser = argparse.ArgumentParser(description='Factory reset iOS Simulator (erase all content)')

    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--udid', help='Simulator UDID to erase')
    target.add_argument('--name', help='Simulator name to erase')
    target.add_argument('--all', action='store_true', help='Erase all simulators')

    args = parser.parse_args()

    # Erase all
    if args.all:
        success, stdout, stderr = run_simctl('erase', 'all')
        if success:
            print(json.dumps({
                'success': True,
                'message': 'Erased all simulators (factory reset)',
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Failed to erase all simulators: {stderr.strip()}',
                'hint': 'Simulators must be shut down before erasing. Use sim-shutdown.py --all first.'
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

    # Erase the device
    success, stdout, stderr = run_simctl('erase', udid)

    if not success:
        ok, response = handle_simctl_result(
            success, stderr, operation='erase simulator',
            context={'udid': udid}
        )
        if not ok:
            response['hint'] = 'The simulator must be shut down before erasing. Use sim-shutdown.py first.'
            print(json.dumps(response))
            sys.exit(1)
        print(json.dumps(response))
        return

    result = {
        'success': True,
        'message': f'Erased simulator {device_name or udid} (factory reset)',
        'udid': udid,
    }
    if device_name:
        result['name'] = device_name

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
