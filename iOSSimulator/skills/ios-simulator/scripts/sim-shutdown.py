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

import subprocess
import json
import sys
import argparse


def run_simctl(*args):
    """Run xcrun simctl command and return output."""
    cmd = ['xcrun', 'simctl'] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


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
            print(json.dumps({
                'success': False,
                'error': error.strip() if error else 'Failed to shutdown simulators'
            }))
            sys.exit(1)
        return

    success, error = shutdown_simulator(args.udid)

    if not success:
        # Check if already shutdown
        if 'current state: Shutdown' in error:
            print(json.dumps({
                'success': True,
                'message': 'Simulator already shutdown',
                'udid': args.udid
            }))
            return

        print(json.dumps({
            'success': False,
            'error': error.strip()
        }))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': 'Simulator shutdown successfully',
        'udid': args.udid
    }))


if __name__ == '__main__':
    main()
