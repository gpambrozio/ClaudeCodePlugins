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

# Check if we're on macOS and can use Quartz
try:
    from Quartz import (
        CGEventCreateMouseEvent,
        CGEventPost,
        CGEventSetIntegerValueField,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGHIDEventTap,
        kCGMouseEventClickState,
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


def get_booted_simulator():
    """Get the first booted simulator's UDID and name."""
    cmd = ['xcrun', 'simctl', 'list', '-j', 'devices']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, None

    data = json.loads(result.stdout)
    for runtime, devices in data.get('devices', {}).items():
        for device in devices:
            if device.get('state') == 'Booted':
                return device.get('udid'), device.get('name')
    return None, None


def get_simulator_window_info(device_name=None):
    """Get Simulator window position and size."""
    if not HAS_QUARTZ:
        return None

    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

    for window in window_list:
        owner = window.get('kCGWindowOwnerName', '')
        name = window.get('kCGWindowName', '')

        # Look for Simulator windows
        if owner == 'Simulator':
            # If device_name specified, try to match it
            if device_name and device_name not in name:
                continue

            bounds = window.get('kCGWindowBounds', {})
            return {
                'x': bounds.get('X', 0),
                'y': bounds.get('Y', 0),
                'width': bounds.get('Width', 0),
                'height': bounds.get('Height', 0),
                'name': name
            }
    return None


def activate_simulator():
    """Bring Simulator.app to front."""
    script = 'tell application "Simulator" to activate'
    subprocess.run(['osascript', '-e', script], capture_output=True)
    time.sleep(0.2)  # Wait for activation


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

    # Activate Simulator
    activate_simulator()

    if HAS_QUARTZ:
        # Get window info
        window_info = get_simulator_window_info(device_name)
        if not window_info:
            print(json.dumps({
                'success': False,
                'error': 'Could not find Simulator window. Is it visible?'
            }))
            sys.exit(1)

        # Calculate window coordinates
        # The simulator screen starts below the window title bar and device chrome
        # These offsets are approximate - the bezel varies by device
        TITLE_BAR_HEIGHT = 28
        DEVICE_TOP_BEZEL = 50  # Approximate bezel height

        window_x = window_info['x'] + args.x + 20  # Left bezel
        window_y = window_info['y'] + TITLE_BAR_HEIGHT + DEVICE_TOP_BEZEL + args.y

        # Perform tap
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
        # Fallback to AppleScript
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
