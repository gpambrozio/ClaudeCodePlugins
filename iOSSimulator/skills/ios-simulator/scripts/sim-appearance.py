#!/usr/bin/env python3
"""
Set the appearance (light/dark mode) on an iOS Simulator.

Usage:
    sim-appearance.py --mode <light|dark> [--udid <udid>]
    sim-appearance.py light
    sim-appearance.py dark

Options:
    --mode <mode>  Appearance mode: light or dark
    --udid <udid>  Simulator UDID (uses booted if not specified)

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


def set_appearance(udid, mode):
    """Set appearance mode on the simulator."""
    success, stdout, stderr = run_simctl('ui', udid, 'appearance', mode)
    return success, stderr


def main():
    parser = argparse.ArgumentParser(description='Set appearance on iOS Simulator')
    parser.add_argument('--mode', '-m', choices=['light', 'dark'],
                        help='Appearance mode')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('mode_positional', nargs='?', choices=['light', 'dark'],
                        help='Appearance mode (positional)')
    args = parser.parse_args()

    # Get mode from either flag or positional
    mode = args.mode or args.mode_positional
    if not mode:
        print(json.dumps({
            'success': False,
            'error': 'Mode is required. Use --mode or provide "light" or "dark"'
        }))
        sys.exit(1)

    # Get UDID
    udid = args.udid
    if not udid:
        udid = get_booted_simulator()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    # Set appearance
    success, error = set_appearance(udid, mode)

    if not success:
        print(json.dumps({
            'success': False,
            'error': error.strip() if error else 'Failed to set appearance'
        }))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': f'Appearance set to {mode}',
        'mode': mode,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
