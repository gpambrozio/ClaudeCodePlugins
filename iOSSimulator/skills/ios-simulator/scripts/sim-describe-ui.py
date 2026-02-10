#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pyobjc-framework-ApplicationServices>=10.0",
#     "pyobjc-framework-Quartz>=10.0",
# ]
# ///
"""
Describe the UI hierarchy of the frontmost iOS Simulator screen.

This script uses macOS Accessibility APIs to inspect the Simulator window
and extract the accessibility tree of the iOS app's UI elements.

Usage:
    sim-describe-ui.py [--udid <udid>] [--format <format>] [--max-depth <n>]

Options:
    --udid <udid>       Simulator UDID (uses booted if not specified)
    --format <format>   Output format: 'nested' (default) or 'flat'
    --max-depth <n>     Maximum depth to traverse (default: 20)
    --point <x,y>       Describe element at specific coordinates
    --include-chrome    Include simulator chrome (menus, hardware buttons)
                        By default, only iOS app UI elements are shown

    Finding elements (combinable filters):
    --find-text <text>  Find elements containing text (case-insensitive, fuzzy)
    --find-exact <text> Find elements with exact text match
    --find-type <type>  Find elements by AXRole (e.g., AXButton, AXStaticText)
    --find-id <id>      Find elements by AXIdentifier
    --index <n>         Return only the Nth match (0-based). Without this, all matches are returned.

Output:
    JSON object containing the UI element hierarchy with:
    - AXRole: Element type (button, staticText, etc.)
    - AXLabel: Accessibility label
    - AXValue: Current value
    - AXFrame: Position and size {x, y, width, height} in simulator coordinates
    - children: Nested child elements (in nested format)

    When using --find-* options, returns matched elements with:
    - All standard attributes
    - center: {x, y} center point for use with sim-tap.py

Notes:
    - Requires Accessibility permissions in System Preferences
    - The simulator must be visible on screen
    - Coordinates are relative to the iOS screen (0,0 = top-left of app)
    - Use --include-chrome for absolute screen coordinates
"""

import subprocess
import json
import sys
import argparse
from typing import Any, Optional

# Note: We can't use sim_utils here because this script uses uv for dependency management
# and needs to be self-contained. The duplication is intentional.

# Import macOS accessibility APIs
try:
    from ApplicationServices import (
        AXUIElementCreateSystemWide,
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
        AXUIElementCopyAttributeNames,
        AXUIElementCopyElementAtPosition,
        AXValueGetType,
        AXValueGetValue,
        kAXValueCGPointType,
        kAXValueCGSizeType,
        kAXValueCGRectType,
        kAXErrorSuccess,
    )
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
    import Quartz
    HAS_ACCESSIBILITY = True
except ImportError as e:
    HAS_ACCESSIBILITY = False
    IMPORT_ERROR = str(e)


def get_booted_simulator() -> tuple[Optional[str], Optional[str]]:
    """Get the first booted simulator's UDID and name.

    Note: This function is duplicated here because this script uses uv
    for dependency management and needs to be self-contained.
    """
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


def get_simulator_pid() -> Optional[int]:
    """Get the process ID of Simulator.app."""
    cmd = ['pgrep', '-x', 'Simulator']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return int(result.stdout.strip().split('\n')[0])
    return None


def get_simulator_window_info(device_name: Optional[str] = None) -> Optional[dict]:
    """Get Simulator window position and size."""
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

    # Collect all Simulator windows
    sim_windows = []
    for window in window_list:
        owner = window.get('kCGWindowOwnerName', '')
        if owner == 'Simulator':
            bounds = window.get('kCGWindowBounds', {})
            # Skip windows with no size (menu bar items, etc.)
            if bounds.get('Width', 0) > 100 and bounds.get('Height', 0) > 100:
                sim_windows.append({
                    'x': bounds.get('X', 0),
                    'y': bounds.get('Y', 0),
                    'width': bounds.get('Width', 0),
                    'height': bounds.get('Height', 0),
                    'name': window.get('kCGWindowName') or device_name or 'Simulator',
                    'pid': window.get('kCGWindowOwnerPID')
                })

    if not sim_windows:
        return None

    # If we have device_name, try to find matching window
    if device_name:
        for win in sim_windows:
            if device_name in (win.get('name') or ''):
                return win

    # Return the first (frontmost) Simulator window
    return sim_windows[0]


def ax_value_to_python(value: Any) -> Any:
    """Convert AXValue types to Python-native types."""
    if value is None:
        return None

    # Handle AXValue types (CGPoint, CGSize, CGRect)
    # pyobjc returns the value directly without needing AXValueGetValue
    try:
        value_type = AXValueGetType(value)
        if value_type == kAXValueCGPointType:
            # For pyobjc, use AXValueGetValue with None as last param
            success, point = AXValueGetValue(value, kAXValueCGPointType, None)
            if success and point:
                return {'x': float(point.x), 'y': float(point.y)}
        elif value_type == kAXValueCGSizeType:
            success, size = AXValueGetValue(value, kAXValueCGSizeType, None)
            if success and size:
                return {'width': float(size.width), 'height': float(size.height)}
        elif value_type == kAXValueCGRectType:
            success, rect = AXValueGetValue(value, kAXValueCGRectType, None)
            if success and rect:
                return {
                    'x': float(rect.origin.x),
                    'y': float(rect.origin.y),
                    'width': float(rect.size.width),
                    'height': float(rect.size.height)
                }
    except (TypeError, AttributeError, ValueError):
        pass

    # Handle basic types
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [ax_value_to_python(v) for v in value]

    # Try to convert to string as fallback
    try:
        return str(value)
    except Exception:
        return None


def get_ax_attribute(element: Any, attribute: str) -> Any:
    """Get a single accessibility attribute value."""
    error, value = AXUIElementCopyAttributeValue(element, attribute, None)
    if error == kAXErrorSuccess:
        return ax_value_to_python(value)
    return None


def get_ax_attributes(element: Any) -> list[str]:
    """Get list of all attribute names for an element."""
    error, names = AXUIElementCopyAttributeNames(element, None)
    if error == kAXErrorSuccess and names:
        return list(names)
    return []


def element_to_dict(element: Any, max_depth: int = 20, current_depth: int = 0) -> Optional[dict]:
    """Convert an AXUIElement to a dictionary representation."""
    if current_depth > max_depth:
        return {'truncated': True, 'reason': 'max_depth_exceeded'}

    # Get all available attributes
    attributes = get_ax_attributes(element)

    # Build element info with key attributes
    info = {}

    # Standard attributes we want to capture
    key_attrs = [
        'AXRole', 'AXRoleDescription', 'AXSubrole',
        'AXTitle', 'AXDescription', 'AXLabel', 'AXValue',
        'AXFrame',
        'AXEnabled', 'AXFocused', 'AXSelected',
        'AXHelp', 'AXIdentifier', 'AXPlaceholderValue'
    ]

    for attr in key_attrs:
        if attr in attributes:
            value = get_ax_attribute(element, attr)
            if value is not None:
                info[attr] = value

    # Compute frame from position and size if not directly available
    if 'AXFrame' not in info and 'AXPosition' in attributes and 'AXSize' in attributes:
        pos = get_ax_attribute(element, 'AXPosition')
        size = get_ax_attribute(element, 'AXSize')
        if isinstance(pos, dict) and isinstance(size, dict):
            info['AXFrame'] = {
                'x': pos.get('x', 0),
                'y': pos.get('y', 0),
                'width': size.get('width', 0),
                'height': size.get('height', 0)
            }

    # Get children recursively
    if 'AXChildren' in attributes:
        error, children = AXUIElementCopyAttributeValue(element, 'AXChildren', None)
        if error == kAXErrorSuccess and children:
            child_list = []
            for child in children:
                child_dict = element_to_dict(child, max_depth, current_depth + 1)
                if child_dict:
                    child_list.append(child_dict)
            if child_list:
                info['children'] = child_list

    return info if info else None


def flatten_tree(tree: dict, flat_list: list, parent_path: str = "") -> None:
    """Flatten a nested tree into a list of elements with paths."""
    if not tree:
        return

    # Create a copy without children for the flat entry
    entry = {k: v for k, v in tree.items() if k != 'children'}

    # Add path info
    role = tree.get('AXRole', 'unknown')
    label = tree.get('AXLabel') or tree.get('AXTitle') or tree.get('AXDescription') or ''
    entry['path'] = f"{parent_path}/{role}[{label}]" if parent_path else f"/{role}[{label}]"

    flat_list.append(entry)

    # Process children
    for i, child in enumerate(tree.get('children', [])):
        flatten_tree(child, flat_list, entry['path'])


def calculate_center(frame: dict) -> dict:
    """Calculate center point from an AXFrame dict."""
    return {
        'x': round(frame.get('x', 0) + frame.get('width', 0) / 2),
        'y': round(frame.get('y', 0) + frame.get('height', 0) / 2)
    }


def element_matches_text(element: dict, text: str, fuzzy: bool = True) -> bool:
    """Check if an element's text fields contain the search text."""
    searchable = ' '.join(filter(None, [
        element.get('AXLabel'),
        element.get('AXTitle'),
        element.get('AXDescription'),
        element.get('AXValue'),
        element.get('AXPlaceholderValue'),
    ]))
    if fuzzy:
        return text.lower() in searchable.lower()
    return text in [
        element.get('AXLabel'),
        element.get('AXTitle'),
        element.get('AXDescription'),
        element.get('AXValue'),
        element.get('AXPlaceholderValue'),
    ]


def find_elements(tree: dict,
                  text: Optional[str] = None,
                  exact_text: Optional[str] = None,
                  element_type: Optional[str] = None,
                  identifier: Optional[str] = None) -> list[dict]:
    """Find elements in the tree matching the given criteria.

    All criteria are combined with AND logic.

    Args:
        tree: The accessibility tree (nested format)
        text: Fuzzy text search (case-insensitive substring match)
        exact_text: Exact text match against label/title/description/value
        element_type: Match AXRole (e.g., 'AXButton', 'AXStaticText')
        identifier: Match AXIdentifier exactly

    Returns:
        List of matching element dicts, each with a 'center' field added.
    """
    flat_list: list[dict] = []
    flatten_tree(tree, flat_list)

    matches = []
    for element in flat_list:
        if element_type and element.get('AXRole') != element_type:
            continue
        if identifier and element.get('AXIdentifier') != identifier:
            continue
        if text and not element_matches_text(element, text, fuzzy=True):
            continue
        if exact_text and not element_matches_text(element, exact_text, fuzzy=False):
            continue

        # Add center point for easy use with sim-tap.py
        frame = element.get('AXFrame')
        if frame:
            element = dict(element)
            element['center'] = calculate_center(frame)
        matches.append(element)

    return matches


def find_ios_content_group(tree: dict) -> Optional[dict]:
    """Find the iOSContentGroup element in the accessibility tree."""
    if not tree:
        return None

    # Check if this is the iOS content group
    if tree.get('AXSubrole') == 'iOSContentGroup':
        return tree

    # Search children recursively
    for child in tree.get('children', []):
        found = find_ios_content_group(child)
        if found:
            return found

    return None


def convert_to_simulator_coordinates(tree: dict, content_origin: dict) -> dict:
    """Convert absolute screen coordinates to simulator-relative coordinates."""
    if not tree:
        return tree

    result = dict(tree)

    # Convert AXFrame coordinates
    if 'AXFrame' in result:
        frame = result['AXFrame']
        result['AXFrame'] = {
            'x': frame['x'] - content_origin['x'],
            'y': frame['y'] - content_origin['y'],
            'width': frame['width'],
            'height': frame['height']
        }

    # Process children recursively
    if 'children' in result:
        result['children'] = [
            convert_to_simulator_coordinates(child, content_origin)
            for child in result['children']
        ]

    return result


def describe_simulator_ui(device_name: Optional[str] = None,
                          output_format: str = 'nested',
                          max_depth: int = 20,
                          ios_only: bool = True) -> dict:
    """Describe the UI hierarchy of the Simulator.

    Args:
        device_name: Optional device name to match
        output_format: 'nested' or 'flat'
        max_depth: Maximum depth to traverse
        ios_only: If True, only return iOS app elements (not simulator chrome)
    """

    # Get simulator PID
    sim_pid = get_simulator_pid()
    if not sim_pid:
        return {
            'success': False,
            'error': 'Simulator.app is not running'
        }

    # Get window info for context
    window_info = get_simulator_window_info(device_name)
    if not window_info:
        return {
            'success': False,
            'error': 'No Simulator window found. Is it visible on screen?'
        }

    # Create AXUIElement for the Simulator application
    app_element = AXUIElementCreateApplication(sim_pid)
    if not app_element:
        return {
            'success': False,
            'error': 'Could not create accessibility element for Simulator'
        }

    # Get the full accessibility tree
    tree = element_to_dict(app_element, max_depth)

    if not tree:
        return {
            'success': False,
            'error': 'Could not read accessibility tree. Check Accessibility permissions in System Preferences > Privacy & Security > Accessibility'
        }

    # Filter to iOS content only if requested
    content_origin = None
    if ios_only:
        ios_content = find_ios_content_group(tree)
        if ios_content:
            # Get the origin of the iOS content area for coordinate conversion
            frame = ios_content.get('AXFrame') or {}
            content_origin = {
                'x': frame.get('x', 0),
                'y': frame.get('y', 0)
            }
            # Convert coordinates to be relative to the iOS content area
            tree = convert_to_simulator_coordinates(ios_content, content_origin)
        else:
            return {
                'success': False,
                'error': 'Could not find iOS content area in simulator. The simulator window may not be fully loaded.'
            }

    result = {
        'success': True,
        'simulator': {
            'name': window_info.get('name', 'Unknown'),
            'window': {
                'x': window_info.get('x'),
                'y': window_info.get('y'),
                'width': window_info.get('width'),
                'height': window_info.get('height')
            }
        }
    }

    # Add iOS content area info if we filtered
    if content_origin:
        result['ios_content_area'] = {
            'screen_origin': content_origin,
            'note': 'Coordinates are relative to iOS screen (0,0 = top-left of app)'
        }

    if output_format == 'flat':
        flat_list = []
        flatten_tree(tree, flat_list)
        result['elements'] = flat_list
        result['count'] = len(flat_list)
    else:
        result['tree'] = tree

    return result


def describe_element_at_point(x: float, y: float, device_name: Optional[str] = None) -> dict:
    """Describe the UI element at a specific screen coordinate."""

    # Get window info to calculate absolute position
    window_info = get_simulator_window_info(device_name)
    if not window_info:
        return {
            'success': False,
            'error': 'No Simulator window found'
        }

    # Calculate absolute screen position
    # Account for window position and estimated bezel
    TITLE_BAR_HEIGHT = 28
    DEVICE_TOP_BEZEL = 50
    LEFT_BEZEL = 20

    abs_x = window_info['x'] + LEFT_BEZEL + x
    abs_y = window_info['y'] + TITLE_BAR_HEIGHT + DEVICE_TOP_BEZEL + y

    # Get element at position
    system_wide = AXUIElementCreateSystemWide()
    error, element = AXUIElementCopyElementAtPosition(system_wide, abs_x, abs_y, None)

    if error != kAXErrorSuccess or not element:
        return {
            'success': False,
            'error': f'No element found at point ({x}, {y})',
            'absolute_position': {'x': abs_x, 'y': abs_y}
        }

    info = element_to_dict(element, max_depth=1)

    return {
        'success': True,
        'point': {'x': x, 'y': y},
        'absolute_position': {'x': abs_x, 'y': abs_y},
        'element': info
    }


def main():
    parser = argparse.ArgumentParser(description='Describe iOS Simulator UI hierarchy')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('--format', choices=['nested', 'flat'], default='nested',
                        help='Output format (default: nested)')
    parser.add_argument('--max-depth', type=int, default=20,
                        help='Maximum depth to traverse (default: 20)')
    parser.add_argument('--point', help='Describe element at x,y coordinates (e.g., "100,200")')
    parser.add_argument('--include-chrome', action='store_true',
                        help='Include simulator chrome (menus, buttons) in output. '
                             'By default, only iOS app elements are shown.')

    # Element finding options
    find_group = parser.add_argument_group('element finding',
                                           'Find specific elements (filters are combined with AND)')
    find_group.add_argument('--find-text',
                            help='Find elements containing text (case-insensitive)')
    find_group.add_argument('--find-exact',
                            help='Find elements with exact text match')
    find_group.add_argument('--find-type',
                            help='Find elements by AXRole (e.g., AXButton, AXStaticText)')
    find_group.add_argument('--find-id',
                            help='Find elements by AXIdentifier')
    find_group.add_argument('--index', type=int, default=None,
                            help='Return only the Nth match (0-based)')

    args = parser.parse_args()

    if not HAS_ACCESSIBILITY:
        print(json.dumps({
            'success': False,
            'error': f'Missing required dependencies: {IMPORT_ERROR}',
            'hint': 'Run this script with: uv run sim-describe-ui.py'
        }))
        sys.exit(1)

    # Get booted simulator for context
    udid, device_name = get_booted_simulator()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    has_find = any([args.find_text, args.find_exact, args.find_type, args.find_id])

    if args.point:
        # Describe element at specific point
        try:
            x, y = map(float, args.point.split(','))
            result = describe_element_at_point(x, y, device_name)
        except ValueError:
            print(json.dumps({
                'success': False,
                'error': 'Invalid point format. Use: --point x,y (e.g., --point 100,200)'
            }))
            sys.exit(1)
    elif has_find:
        # Find elements matching criteria
        ios_only = not args.include_chrome
        ui_result = describe_simulator_ui(device_name, 'nested', args.max_depth, ios_only)
        if not ui_result.get('success'):
            result = ui_result
        else:
            tree = ui_result.get('tree', {})
            matches = find_elements(
                tree,
                text=args.find_text,
                exact_text=args.find_exact,
                element_type=args.find_type,
                identifier=args.find_id,
            )

            if args.index is not None:
                if 0 <= args.index < len(matches):
                    matches = [matches[args.index]]
                else:
                    matches = []

            result = {
                'success': len(matches) > 0,
                'count': len(matches),
                'matches': matches,
            }
            if not matches:
                criteria = []
                if args.find_text:
                    criteria.append(f"text~'{args.find_text}'")
                if args.find_exact:
                    criteria.append(f"text='{args.find_exact}'")
                if args.find_type:
                    criteria.append(f"type={args.find_type}")
                if args.find_id:
                    criteria.append(f"id={args.find_id}")
                if args.index is not None:
                    criteria.append(f"index={args.index}")
                result['error'] = f"No elements found matching: {', '.join(criteria)}"
    else:
        # Describe full UI hierarchy
        ios_only = not args.include_chrome
        result = describe_simulator_ui(device_name, args.format, args.max_depth, ios_only)

    print(json.dumps(result, indent=2))

    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
