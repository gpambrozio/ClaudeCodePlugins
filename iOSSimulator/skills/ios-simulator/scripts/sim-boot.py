#!/usr/bin/env python3
"""
Boot an iOS Simulator.

Usage:
    sim-boot.py --udid <udid>
    sim-boot.py --name <name> [--runtime <runtime>]

Options:
    --udid <udid>        Boot simulator by UDID
    --name <name>        Boot simulator by name (e.g., "iPhone 15")
    --runtime <runtime>  Specify runtime when using --name (e.g., "iOS-17-0")

Output:
    JSON object with success status and simulator info
"""

import json
import sys
import argparse

from sim_utils import run_simctl, find_simulator_by_name, open_simulator_app


def boot_simulator(udid):
    """Boot a simulator by UDID."""
    success, stdout, stderr = run_simctl('boot', udid)
    return success, stderr


def main():
    parser = argparse.ArgumentParser(description='Boot an iOS Simulator')
    parser.add_argument('--udid', help='Simulator UDID')
    parser.add_argument('--name', help='Simulator name (e.g., "iPhone 15")')
    parser.add_argument('--runtime', help='Runtime filter (e.g., "iOS-17")')
    parser.add_argument('--no-open', action='store_true', help='Do not open Simulator.app')
    args = parser.parse_args()

    if not args.udid and not args.name:
        print(json.dumps({
            'success': False,
            'error': 'Either --udid or --name is required'
        }))
        sys.exit(1)

    udid = args.udid
    sim_info = None

    # Find by name if no UDID provided
    if not udid:
        sim_info = find_simulator_by_name(args.name, args.runtime)
        if not sim_info:
            print(json.dumps({
                'success': False,
                'error': f'No available simulator found with name "{args.name}"'
            }))
            sys.exit(1)
        udid = sim_info['udid']

    # Check if already booted
    if sim_info and sim_info.get('state') == 'Booted':
        if not args.no_open:
            open_simulator_app()
        print(json.dumps({
            'success': True,
            'message': 'Simulator already booted',
            'udid': udid,
            'name': sim_info.get('name', 'Unknown'),
            'runtime': sim_info.get('runtime', 'Unknown')
        }))
        return

    # Boot the simulator
    success, error = boot_simulator(udid)

    if not success:
        # Check if error is "already booted"
        if 'Unable to boot device in current state: Booted' in error:
            if not args.no_open:
                open_simulator_app()
            print(json.dumps({
                'success': True,
                'message': 'Simulator already booted',
                'udid': udid
            }))
            return

        print(json.dumps({
            'success': False,
            'error': error.strip()
        }))
        sys.exit(1)

    # Open Simulator.app unless --no-open
    if not args.no_open:
        open_simulator_app()

    result = {
        'success': True,
        'message': 'Simulator booted successfully',
        'udid': udid
    }
    if sim_info:
        result['name'] = sim_info.get('name')
        result['runtime'] = sim_info.get('runtime')

    print(json.dumps(result))


if __name__ == '__main__':
    main()
