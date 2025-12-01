#!/usr/bin/env python3
"""
Set the iOS Simulator window to "Point Accurate" size mode.

Usage:
    sim-point-accurate.py

This ensures that screen coordinates in the Simulator match iOS point
coordinates, making tap/swipe commands accurate.

The script uses the Window > Point Accurate menu item (Cmd+2).
"""

import subprocess
import json
import sys
import time


def set_point_accurate():
    """Set Simulator to Point Accurate mode via menu or keyboard shortcut."""
    script = '''
    tell application "Simulator"
        activate
    end tell

    delay 0.2

    tell application "System Events"
        tell process "Simulator"
            -- Use keyboard shortcut Cmd+2 for Point Accurate
            keystroke "2" using {command down}
        end tell
    end tell
    '''

    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def main():
    success, error = set_point_accurate()

    if success:
        print(json.dumps({
            'success': True,
            'message': 'Simulator set to Point Accurate mode'
        }))
    else:
        print(json.dumps({
            'success': False,
            'error': error.strip() if error else 'Failed to set Point Accurate mode'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
