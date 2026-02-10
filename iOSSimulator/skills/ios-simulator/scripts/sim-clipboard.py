#!/usr/bin/env python3
"""
Manage the iOS Simulator clipboard (pasteboard).

Copy text to or read text from the simulator's clipboard.

Usage:
    sim-clipboard.py --set "text to copy"
    sim-clipboard.py --get

Options:
    --set <text>        Copy text to the simulator clipboard
    --get               Read current clipboard contents
    --udid <udid>       Simulator UDID (uses booted if not specified)

Output:
    JSON object with success status and clipboard contents.

Notes:
    - Use --set to prepare text for paste testing
    - Use --get to verify clipboard state
    - After --set, use sim-keyboard.py to trigger Cmd+V paste
"""

import json
import subprocess
import sys
import argparse

from sim_utils import get_booted_simulator_udid


def clipboard_set(udid, text):
    """Copy text to the simulator clipboard.

    Uses subprocess directly since pbcopy reads from stdin.

    Returns:
        Tuple of (success, error_message)
    """
    cmd = ['xcrun', 'simctl', 'pbcopy', udid]
    result = subprocess.run(cmd, input=text, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, None


def clipboard_get(udid):
    """Read the simulator clipboard contents.

    Returns:
        Tuple of (success, text_or_error)
    """
    cmd = ['xcrun', 'simctl', 'pbpaste', udid]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, result.stdout


def main():
    parser = argparse.ArgumentParser(description='Manage iOS Simulator clipboard')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--set', dest='set_text', help='Copy text to clipboard')
    action.add_argument('--get', dest='get_clipboard', action='store_true',
                        help='Read clipboard contents')

    args = parser.parse_args()

    # Get UDID
    udid = args.udid
    if not udid:
        udid = get_booted_simulator_udid()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    if args.set_text is not None:
        success, error = clipboard_set(udid, args.set_text)
        if success:
            print(json.dumps({
                'success': True,
                'message': 'Text copied to clipboard',
                'text': args.set_text,
                'length': len(args.set_text),
                'udid': udid,
            }, indent=2))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Failed to set clipboard: {error}',
                'udid': udid,
            }))
            sys.exit(1)

    elif args.get_clipboard:
        success, result = clipboard_get(udid)
        if success:
            print(json.dumps({
                'success': True,
                'text': result,
                'length': len(result),
                'udid': udid,
            }, indent=2))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Failed to read clipboard: {result}',
                'udid': udid,
            }))
            sys.exit(1)


if __name__ == '__main__':
    main()
