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
    --no-open            Don't open Simulator.app window
    --no-wait            Don't wait for the simulator to be ready
    --timeout <seconds>  Max seconds to wait for readiness (default: 60)

Output:
    JSON object with success status, simulator info, and boot time
"""

import json
import sys
import time
import argparse
import subprocess

from sim_utils import run_simctl, find_simulator_by_name, open_simulator_app, handle_simctl_result


def boot_simulator(udid):
    """Boot a simulator by UDID."""
    success, stdout, stderr = run_simctl('boot', udid)
    return success, stderr


def wait_for_ready(udid, timeout=60):
    """Wait until the simulator is ready to accept commands.

    Polls by trying to spawn a process on the simulator. When it succeeds,
    the simulator is ready.

    Returns:
        Tuple of (ready: bool, elapsed_seconds: float)
    """
    start = time.time()
    poll_interval = 1.0

    while (time.time() - start) < timeout:
        result = subprocess.run(
            ['xcrun', 'simctl', 'spawn', udid, 'launchctl', 'print', 'system'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return True, round(time.time() - start, 1)

        time.sleep(poll_interval)

    return False, round(time.time() - start, 1)


def main():
    parser = argparse.ArgumentParser(description='Boot an iOS Simulator')
    parser.add_argument('--udid', help='Simulator UDID')
    parser.add_argument('--name', help='Simulator name (e.g., "iPhone 15")')
    parser.add_argument('--runtime', help='Runtime filter (e.g., "iOS-17")')
    parser.add_argument('--no-open', action='store_true', help='Do not open Simulator.app')
    parser.add_argument('--no-wait', action='store_true',
                        help='Do not wait for the simulator to be ready')
    parser.add_argument('--timeout', type=int, default=60,
                        help='Max seconds to wait for readiness (default: 60)')
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

    boot_start = time.time()

    # Boot the simulator
    success, error = boot_simulator(udid)

    if not success:
        actual_success, response = handle_simctl_result(
            success, error, operation='boot',
            context={'udid': udid}
        )

        if actual_success:
            # Non-error condition (already booted)
            if not args.no_open:
                open_simulator_app()
            response['udid'] = udid
            print(json.dumps(response))
            return

        print(json.dumps(response))
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

    # Wait for readiness
    if not args.no_wait:
        ready, wait_time = wait_for_ready(udid, timeout=args.timeout)
        result['boot_time_seconds'] = round(time.time() - boot_start, 1)
        if ready:
            result['ready'] = True
        else:
            result['ready'] = False
            result['message'] = f'Simulator booted but not ready after {args.timeout}s'

    print(json.dumps(result))


if __name__ == '__main__':
    main()
