#!/usr/bin/env python3
"""
Type text into an iOS Simulator.

Usage:
    sim-type.py --text <text>
    sim-type.py "Hello, World!"
    sim-type.py --clear --text <text>

Options:
    --text <text>  Text to type
    --clear        Clear the focused text field before typing (Cmd+A then Delete)
    --slow         Type character by character (slower but more reliable)
    --udid <udid>  Simulator UDID (uses booted if not specified)

Notes:
    - Make sure a text field is focused before typing
    - Uses keyboard simulation via System Events
    - Special characters and emojis are supported
    - Use --clear to replace existing text in a field

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse
import time

from sim_utils import get_booted_simulator_udid


def activate_simulator():
    """Bring Simulator.app to front."""
    script = 'tell application "Simulator" to activate'
    subprocess.run(['osascript', '-e', script], capture_output=True)
    time.sleep(0.2)


def type_text(text):
    """Type text using System Events keystroke."""
    # Escape special characters for AppleScript
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')

    script = f'''
    tell application "Simulator" to activate
    delay 0.1
    tell application "System Events"
        keystroke "{escaped}"
    end tell
    '''

    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def clear_text_field():
    """Clear text in the focused field by selecting all then deleting."""
    script = '''
    tell application "Simulator" to activate
    delay 0.1
    tell application "System Events"
        keystroke "a" using {command down}
        delay 0.1
        key code 51
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def type_text_slow(text, delay=0.05):
    """Type text character by character (more reliable for some apps)."""
    activate_simulator()

    for char in text:
        # Escape special characters
        if char == '"':
            escaped = '\\"'
        elif char == '\\':
            escaped = '\\\\'
        else:
            escaped = char

        script = f'''
        tell application "System Events"
            keystroke "{escaped}"
        end tell
        '''
        subprocess.run(['osascript', '-e', script], capture_output=True)
        time.sleep(delay)

    return True


def main():
    parser = argparse.ArgumentParser(description='Type text on iOS Simulator')
    parser.add_argument('--text', '-t', help='Text to type')
    parser.add_argument('--slow', action='store_true',
                        help='Type character by character (slower but more reliable)')
    parser.add_argument('--clear', action='store_true',
                        help='Clear the focused text field before typing (Cmd+A then Delete)')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('text_positional', nargs='?', help='Text to type (positional)')
    args = parser.parse_args()

    # Get text from either flag or positional
    text = args.text or args.text_positional
    if not text and not args.clear:
        print(json.dumps({
            'success': False,
            'error': 'Text is required. Use --text or provide as argument.'
        }))
        sys.exit(1)

    # Verify simulator is booted
    udid = args.udid or get_booted_simulator_udid()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    # Clear field first if requested
    if args.clear:
        clear_success, clear_error = clear_text_field()
        if not clear_success:
            print(json.dumps({
                'success': False,
                'error': clear_error.strip() if clear_error else 'Failed to clear text field'
            }))
            sys.exit(1)
        if not text:
            # Just clearing, no text to type
            print(json.dumps({
                'success': True,
                'message': 'Cleared text field',
                'udid': udid
            }))
            return
        time.sleep(0.1)

    # Type the text
    if args.slow:
        success = type_text_slow(text)
        error = None
    else:
        success, error = type_text(text)

    if success:
        msg = f'Cleared and typed {len(text)} characters' if args.clear else f'Typed {len(text)} characters'
        print(json.dumps({
            'success': True,
            'message': msg,
            'text_length': len(text),
            'cleared': args.clear,
            'udid': udid
        }))
    else:
        print(json.dumps({
            'success': False,
            'error': error.strip() if error else 'Failed to type text'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
