#!/usr/bin/env python3
"""
Simulate a shake gesture on an iOS Simulator.

Usage:
    sim-shake.py [--udid <udid>]

Options:
    --udid <udid>  Simulator UDID (uses booted if not specified)

Notes:
    - Uses keyboard shortcut Ctrl+Cmd+Z to simulate shake
    - Useful for triggering "Shake to Undo" or other shake-based features

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse
import time

from sim_utils import get_booted_simulator_udid, preserve_focus


def simulate_shake():
    """Simulate shake using keyboard shortcut Ctrl+Cmd+Z."""
    script = '''
    tell application "Simulator" to activate
    delay 0.1
    tell application "System Events"
        keystroke "z" using {control down, command down}
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def main():
    parser = argparse.ArgumentParser(description='Simulate shake gesture on iOS Simulator')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    args = parser.parse_args()

    # Verify simulator is booted
    udid = args.udid or get_booted_simulator_udid()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    with preserve_focus():
        # Simulate shake
        success, error = simulate_shake()

        if success:
            print(json.dumps({
                'success': True,
                'message': 'Shake gesture simulated',
                'udid': udid
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': error.strip() if error else 'Failed to simulate shake'
            }))
            sys.exit(1)


if __name__ == '__main__':
    main()
