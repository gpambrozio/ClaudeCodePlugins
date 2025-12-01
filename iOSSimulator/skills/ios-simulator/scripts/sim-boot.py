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

import subprocess
import json
import sys
import argparse


def run_simctl(*args):
    """Run xcrun simctl command and return output."""
    cmd = ['xcrun', 'simctl'] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def get_simulators():
    """Get all simulators as JSON."""
    cmd = ['xcrun', 'simctl', 'list', '-j', 'devices']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def find_simulator_by_name(name, runtime=None):
    """Find a simulator by name, optionally filtered by runtime."""
    devices_data = get_simulators()
    if not devices_data:
        return None

    matches = []
    for rt, devices in devices_data.get('devices', {}).items():
        if runtime and runtime not in rt:
            continue
        for device in devices:
            if device.get('name') == name and device.get('isAvailable', True):
                matches.append({
                    'udid': device.get('udid'),
                    'name': device.get('name'),
                    'state': device.get('state'),
                    'runtime': rt.split('.')[-1]
                })

    # Return the first match, preferring newer runtimes (sorted desc)
    if matches:
        matches.sort(key=lambda x: x['runtime'], reverse=True)
        return matches[0]
    return None


def boot_simulator(udid):
    """Boot a simulator by UDID."""
    success, stdout, stderr = run_simctl('boot', udid)
    return success, stderr


def open_simulator_app():
    """Open the Simulator.app to show the booted simulator."""
    subprocess.run(['open', '-a', 'Simulator'], capture_output=True)


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
