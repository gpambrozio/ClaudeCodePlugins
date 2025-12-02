#!/usr/bin/env python3
"""
Press the Home button on an iOS Simulator.

Usage:
    sim-home.py [--udid <udid>]

Options:
    --udid <udid>  Simulator UDID (uses booted if not specified)

Notes:
    - Uses keyboard shortcut Cmd+Shift+H to simulate Home button
    - Works on all iPhone/iPad simulators

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse
import time

from sim_utils import get_booted_simulator_udid


def press_home():
    """Press Home button using keyboard shortcut."""
    script = '''
    tell application "Simulator" to activate
    delay 0.1
    tell application "System Events"
        keystroke "h" using {command down, shift down}
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def main():
    parser = argparse.ArgumentParser(description='Press Home button on iOS Simulator')
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

    # Press Home
    success, error = press_home()

    if success:
        print(json.dumps({
            'success': True,
            'message': 'Home button pressed',
            'udid': udid
        }))
    else:
        print(json.dumps({
            'success': False,
            'error': error.strip() if error else 'Failed to press Home button'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
