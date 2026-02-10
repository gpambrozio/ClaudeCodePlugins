#!/usr/bin/env python3
"""
Perform gestures on an iOS Simulator screen.

Supports directional swipes, long press, pull-to-refresh, and slow drag.

Usage:
    sim-swipe.py --up | --down | --left | --right
    sim-swipe.py --from-x <x> --from-y <y> --to-x <x> --to-y <y>
    sim-swipe.py --long-press --x <x> --y <y> [--hold <seconds>]
    sim-swipe.py --pull-to-refresh
    sim-swipe.py --drag --from-x <x> --from-y <y> --to-x <x> --to-y <y>

Options:
    --from-x <x>      Starting X coordinate
    --from-y <y>      Starting Y coordinate
    --to-x <x>        Ending X coordinate
    --to-y <y>        Ending Y coordinate
    --duration <sec>  Swipe duration in seconds (default: 0.3)
    --udid <udid>     Simulator UDID (uses booted if not specified)

Directional shortcuts:
    --up              Swipe up (scroll down) from center
    --down            Swipe down (scroll up) from center
    --left            Swipe left from center
    --right           Swipe right from center

Additional gestures:
    --long-press      Long press at --x, --y for --hold seconds (default: 2.0)
    --pull-to-refresh Pull down from top of screen to trigger refresh
    --drag            Slow drag between --from-x/y and --to-x/y (1.0s duration)

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


def long_press_with_quartz(x, y, hold_duration=2.0):
    """Perform a long press (tap and hold) using Quartz mouse events."""
    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), 0)
    CGEventPost(kCGHIDEventTap, event)

    time.sleep(hold_duration)

    event = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), 0)
    CGEventPost(kCGHIDEventTap, event)


def get_screen_size_from_window(window_info):
    """Estimate the iOS screen size from the simulator window dimensions."""
    TITLE_BAR_HEIGHT = 28
    DEVICE_TOP_BEZEL = 50
    LEFT_BEZEL = 20
    RIGHT_BEZEL = 20
    BOTTOM_BEZEL = 50

    width = window_info['width'] - LEFT_BEZEL - RIGHT_BEZEL
    height = window_info['height'] - TITLE_BAR_HEIGHT - DEVICE_TOP_BEZEL - BOTTOM_BEZEL

    if width > 0 and height > 0:
        return width, height
    return 390, 700  # fallback


def main():
    parser = argparse.ArgumentParser(description='Perform gestures on iOS Simulator screen')
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

    # Additional gestures
    parser.add_argument('--long-press', action='store_true',
                        help='Long press at --x, --y for --hold seconds')
    parser.add_argument('--x', type=int, help='X coordinate for long press')
    parser.add_argument('--y', type=int, help='Y coordinate for long press')
    parser.add_argument('--hold', type=float, default=2.0,
                        help='Hold duration for long press in seconds (default: 2.0)')
    parser.add_argument('--pull-to-refresh', action='store_true',
                        help='Pull down from top to trigger refresh')
    parser.add_argument('--drag', action='store_true',
                        help='Slow drag between --from-x/y and --to-x/y')

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

    # Auto-detect screen size from window dimensions
    screen_width, screen_height = get_screen_size_from_window(window_info)
    center_x = screen_width // 2
    center_y = screen_height // 2
    swipe_distance = 300

    # --- Long press ---
    if args.long_press:
        if args.x is None or args.y is None:
            print(json.dumps({
                'success': False,
                'error': '--long-press requires --x and --y coordinates'
            }))
            sys.exit(1)

        wx, wy = screen_to_window_coords(args.x, args.y, window_info)
        long_press_with_quartz(wx, wy, args.hold)

        print(json.dumps({
            'success': True,
            'message': f'Long pressed at ({args.x}, {args.y}) for {args.hold}s',
            'gesture': 'long_press',
            'x': args.x,
            'y': args.y,
            'hold': args.hold,
            'udid': udid
        }))
        return

    # --- Pull to refresh ---
    if args.pull_to_refresh:
        from_x, from_y = center_x, 80
        to_x, to_y = center_x, screen_height // 2

        start_wx, start_wy = screen_to_window_coords(from_x, from_y, window_info)
        end_wx, end_wy = screen_to_window_coords(to_x, to_y, window_info)

        swipe_with_quartz(start_wx, start_wy, end_wx, end_wy, duration=0.5, steps=25)

        print(json.dumps({
            'success': True,
            'message': 'Performed pull to refresh',
            'gesture': 'pull_to_refresh',
            'from': {'x': from_x, 'y': from_y},
            'to': {'x': to_x, 'y': to_y},
            'udid': udid
        }))
        return

    # --- Drag (slow swipe) ---
    if args.drag:
        if not all([args.from_x is not None, args.from_y is not None,
                    args.to_x is not None, args.to_y is not None]):
            print(json.dumps({
                'success': False,
                'error': '--drag requires --from-x, --from-y, --to-x, --to-y'
            }))
            sys.exit(1)

        start_wx, start_wy = screen_to_window_coords(args.from_x, args.from_y, window_info)
        end_wx, end_wy = screen_to_window_coords(args.to_x, args.to_y, window_info)

        swipe_with_quartz(start_wx, start_wy, end_wx, end_wy, duration=1.0, steps=40)

        print(json.dumps({
            'success': True,
            'message': f'Dragged from ({args.from_x}, {args.from_y}) to ({args.to_x}, {args.to_y})',
            'gesture': 'drag',
            'from': {'x': args.from_x, 'y': args.from_y},
            'to': {'x': args.to_x, 'y': args.to_y},
            'duration': 1.0,
            'udid': udid
        }))
        return

    # --- Directional swipes ---
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
            'error': 'Specify a gesture: --up/--down/--left/--right, --long-press, --pull-to-refresh, --drag, or --from-x/y --to-x/y'
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
        'gesture': 'swipe',
        'from': {'x': from_x, 'y': from_y},
        'to': {'x': to_x, 'y': to_y},
        'duration': args.duration,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
