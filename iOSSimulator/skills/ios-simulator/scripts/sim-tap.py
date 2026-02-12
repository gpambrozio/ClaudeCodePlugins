#!/usr/bin/env python3
"""
Tap at coordinates on an iOS Simulator screen.

Usage:
    sim-tap.py --x <x> --y <y> [--udid <udid>]

Options:
    --x <x>        X coordinate on simulator screen
    --y <y>        Y coordinate on simulator screen
    --udid <udid>  Simulator UDID (uses booted if not specified)
    --duration     Tap duration in seconds (default: 0.1)

Notes:
    - Coordinates are in simulator screen points (not pixels)
    - The script will activate Simulator.app and click at the correct position
    - For retina simulators, coordinates are automatically scaled

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse
import time

from sim_utils import (
    get_booted_simulator, get_simulator_window_info, activate_simulator,
    screen_to_window_coords, preserve_focus,
)

# CGEvent imports for mouse event posting (script-specific)
try:
    from Quartz import (
        CGEventCreateMouseEvent,
        CGEventPost,
        CGEventSetIntegerValueField,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGHIDEventTap,
        kCGMouseEventClickState,
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


def tap_with_quartz(window_x, window_y, duration=0.1):
    """Send tap event using Quartz."""
    # Mouse down
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (window_x, window_y), 0)
    CGEventSetIntegerValueField(event, kCGMouseEventClickState, 1)
    CGEventPost(kCGHIDEventTap, event)

    time.sleep(duration)

    # Mouse up
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (window_x, window_y), 0)
    CGEventSetIntegerValueField(event, kCGMouseEventClickState, 1)
    CGEventPost(kCGHIDEventTap, event)


def tap_with_applescript(sim_x, sim_y):
    """Fallback: use AppleScript to click (less precise)."""
    # This is a fallback that clicks relative to Simulator window
    script = f'''
    tell application "Simulator" to activate
    delay 0.2
    tell application "System Events"
        tell process "Simulator"
            set frontWin to front window
            set winPos to position of frontWin
            set winSize to size of frontWin
            -- Click at offset from window position
            -- Note: this includes window chrome, so coordinates are approximate
            click at {{(item 1 of winPos) + {sim_x} + 20, (item 2 of winPos) + {sim_y} + 80}}
        end tell
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='Tap on iOS Simulator screen')
    parser.add_argument('--x', type=int, required=True, help='X coordinate')
    parser.add_argument('--y', type=int, required=True, help='Y coordinate')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('--duration', type=float, default=0.1, help='Tap duration in seconds')
    args = parser.parse_args()

    # Get booted simulator
    udid, device_name = get_booted_simulator()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    with preserve_focus():
        activate_simulator(point_accurate=True)

        if HAS_QUARTZ:
            window_info = get_simulator_window_info(device_name)
            if not window_info:
                print(json.dumps({
                    'success': False,
                    'error': 'Could not find Simulator window. Is it visible?'
                }))
                sys.exit(1)

            window_x, window_y = screen_to_window_coords(args.x, args.y, window_info)
            tap_with_quartz(window_x, window_y, args.duration)

            print(json.dumps({
                'success': True,
                'message': f'Tapped at ({args.x}, {args.y})',
                'screen_x': args.x,
                'screen_y': args.y,
                'window_x': window_x,
                'window_y': window_y,
                'udid': udid
            }))
        else:
            success = tap_with_applescript(args.x, args.y)
            if success:
                print(json.dumps({
                    'success': True,
                    'message': f'Tapped at approximately ({args.x}, {args.y})',
                    'screen_x': args.x,
                    'screen_y': args.y,
                    'method': 'applescript',
                    'udid': udid
                }))
            else:
                print(json.dumps({
                    'success': False,
                    'error': 'Failed to tap using AppleScript'
                }))
                sys.exit(1)


if __name__ == '__main__':
    main()
