#!/usr/bin/env python3
"""
Perform a swipe gesture on an iOS Simulator screen.

Usage:
    sim-swipe.py --from-x <x> --from-y <y> --to-x <x> --to-y <y> [--duration <sec>]

Options:
    --from-x <x>      Starting X coordinate
    --from-y <y>      Starting Y coordinate
    --to-x <x>        Ending X coordinate
    --to-y <y>        Ending Y coordinate
    --duration <sec>  Swipe duration in seconds (default: 0.3)
    --udid <udid>     Simulator UDID (uses booted if not specified)

Shortcuts:
    --up              Swipe up (scroll down) from center
    --down            Swipe down (scroll up) from center
    --left            Swipe left from center
    --right           Swipe right from center

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse
import time

from sim_utils import get_booted_simulator

try:
    from Quartz import (
        CGEventCreateMouseEvent,
        CGEventPost,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGEventLeftMouseDragged,
        kCGHIDEventTap,
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


def get_simulator_window_info(device_name=None):
    """Get Simulator window position and size."""
    if not HAS_QUARTZ:
        return None

    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

    for window in window_list:
        owner = window.get('kCGWindowOwnerName', '')
        name = window.get('kCGWindowName', '')

        if owner == 'Simulator':
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


def set_point_accurate_mode():
    """Set Simulator to Point Accurate mode (Cmd+2) for correct coordinate mapping."""
    script = '''
    tell application "Simulator" to activate
    delay 0.2
    tell application "System Events"
        tell process "Simulator"
            keystroke "2" using {command down}
        end tell
    end tell
    '''
    subprocess.run(['osascript', '-e', script], capture_output=True)
    time.sleep(0.1)


def activate_simulator():
    """Bring Simulator.app to front and ensure Point Accurate mode."""
    set_point_accurate_mode()  # This also activates the simulator


def screen_to_window_coords(screen_x, screen_y, window_info):
    """Convert simulator screen coords to window coords."""
    TITLE_BAR_HEIGHT = 28
    DEVICE_TOP_BEZEL = 50
    LEFT_BEZEL = 20

    window_x = window_info['x'] + screen_x + LEFT_BEZEL
    window_y = window_info['y'] + TITLE_BAR_HEIGHT + DEVICE_TOP_BEZEL + screen_y
    return window_x, window_y


def swipe_with_quartz(start_x, start_y, end_x, end_y, duration=0.3, steps=20):
    """Perform swipe using Quartz mouse events."""
    # Mouse down at start
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (start_x, start_y), 0)
    CGEventPost(kCGHIDEventTap, event)

    # Move through intermediate points
    step_delay = duration / steps
    for i in range(1, steps + 1):
        progress = i / steps
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress

        event = CGEventCreateMouseEvent(None, kCGEventLeftMouseDragged, (current_x, current_y), 0)
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(step_delay)

    # Mouse up at end
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (end_x, end_y), 0)
    CGEventPost(kCGHIDEventTap, event)


def main():
    parser = argparse.ArgumentParser(description='Swipe on iOS Simulator screen')
    parser.add_argument('--from-x', type=int, help='Starting X coordinate')
    parser.add_argument('--from-y', type=int, help='Starting Y coordinate')
    parser.add_argument('--to-x', type=int, help='Ending X coordinate')
    parser.add_argument('--to-y', type=int, help='Ending Y coordinate')
    parser.add_argument('--duration', type=float, default=0.3, help='Swipe duration in seconds')
    parser.add_argument('--udid', help='Simulator UDID')

    # Shortcut directions
    parser.add_argument('--up', action='store_true', help='Swipe up from center')
    parser.add_argument('--down', action='store_true', help='Swipe down from center')
    parser.add_argument('--left', action='store_true', help='Swipe left from center')
    parser.add_argument('--right', action='store_true', help='Swipe right from center')

    args = parser.parse_args()

    if not HAS_QUARTZ:
        print(json.dumps({
            'success': False,
            'error': 'Quartz module not available. This script requires macOS.'
        }))
        sys.exit(1)

    # Get booted simulator
    udid, device_name = get_booted_simulator()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    activate_simulator()

    # Get window info
    window_info = get_simulator_window_info(device_name)
    if not window_info:
        print(json.dumps({
            'success': False,
            'error': 'Could not find Simulator window'
        }))
        sys.exit(1)

    # Calculate screen dimensions (approximate - varies by device)
    # For a typical iPhone, assume ~390x844 point screen
    screen_width = 390
    screen_height = 700
    center_x = screen_width // 2
    center_y = screen_height // 2
    swipe_distance = 300

    # Handle shortcut directions
    if args.up:
        from_x, from_y = center_x, center_y + swipe_distance // 2
        to_x, to_y = center_x, center_y - swipe_distance // 2
    elif args.down:
        from_x, from_y = center_x, center_y - swipe_distance // 2
        to_x, to_y = center_x, center_y + swipe_distance // 2
    elif args.left:
        from_x, from_y = center_x + swipe_distance // 2, center_y
        to_x, to_y = center_x - swipe_distance // 2, center_y
    elif args.right:
        from_x, from_y = center_x - swipe_distance // 2, center_y
        to_x, to_y = center_x + swipe_distance // 2, center_y
    elif all([args.from_x is not None, args.from_y is not None,
              args.to_x is not None, args.to_y is not None]):
        from_x, from_y = args.from_x, args.from_y
        to_x, to_y = args.to_x, args.to_y
    else:
        print(json.dumps({
            'success': False,
            'error': 'Specify --from-x, --from-y, --to-x, --to-y or use --up/--down/--left/--right'
        }))
        sys.exit(1)

    # Convert to window coordinates
    start_wx, start_wy = screen_to_window_coords(from_x, from_y, window_info)
    end_wx, end_wy = screen_to_window_coords(to_x, to_y, window_info)

    # Perform swipe
    swipe_with_quartz(start_wx, start_wy, end_wx, end_wy, args.duration)

    print(json.dumps({
        'success': True,
        'message': f'Swiped from ({from_x}, {from_y}) to ({to_x}, {to_y})',
        'from': {'x': from_x, 'y': from_y},
        'to': {'x': to_x, 'y': to_y},
        'duration': args.duration,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
