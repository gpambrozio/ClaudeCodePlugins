#!/usr/bin/env python3
"""
Describe UI elements on an iOS Simulator screen using macOS Accessibility APIs.

Usage:
    sim-describe-ui.py [--udid <udid>] [--max-depth <depth>]

Options:
    --udid <udid>        Simulator UDID (uses booted if not specified)
    --max-depth <depth>  Maximum depth to traverse (default: 10)
    --buttons            Show only buttons and tappable elements
    --text-fields        Show only text input fields
    --all                Show all elements (verbose)

Output:
    JSON object with UI element hierarchy including:
    - role: Element type (button, text field, static text, etc.)
    - label: Accessibility label
    - value: Current value (for text fields, etc.)
    - position: Screen coordinates {x, y}
    - size: Element dimensions {width, height}
    - children: Nested child elements

Notes:
    - Requires Accessibility permissions for Terminal/IDE
    - First run may prompt for accessibility access in System Preferences
"""

import subprocess
import json
import sys
import argparse

try:
    from ApplicationServices import (
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
        AXUIElementCopyAttributeNames,
        AXValueGetValue,
        kAXErrorSuccess,
        kAXValueTypeCGPoint,
        kAXValueTypeCGSize,
    )
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
    import Quartz
    HAS_ACCESSIBILITY = True
except ImportError:
    HAS_ACCESSIBILITY = False


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


def get_simulator_pid():
    """Get the PID of Simulator.app."""
    result = subprocess.run(
        ['pgrep', '-x', 'Simulator'],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return int(result.stdout.strip().split('\n')[0])
    return None


def get_ax_attribute(element, attribute):
    """Safely get an accessibility attribute value."""
    err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    if err == kAXErrorSuccess:
        return value
    return None


def get_ax_position(element):
    """Get element position as dict."""
    value = get_ax_attribute(element, "AXPosition")
    if value:
        try:
            # AXPosition is an AXValue containing CGPoint
            point = Quartz.CGPoint()
            if AXValueGetValue(value, kAXValueTypeCGPoint, point):
                return {"x": int(point.x), "y": int(point.y)}
        except:
            pass
    return None


def get_ax_size(element):
    """Get element size as dict."""
    value = get_ax_attribute(element, "AXSize")
    if value:
        try:
            # AXSize is an AXValue containing CGSize
            size = Quartz.CGSize()
            if AXValueGetValue(value, kAXValueTypeCGSize, size):
                return {"width": int(size.width), "height": int(size.height)}
        except:
            pass
    return None


def element_to_dict(element, depth=0, max_depth=10, filter_type=None):
    """Convert an AXUIElement to a dictionary representation."""
    if depth > max_depth:
        return None

    # Get basic attributes
    role = get_ax_attribute(element, "AXRole")
    subrole = get_ax_attribute(element, "AXSubrole")
    title = get_ax_attribute(element, "AXTitle")
    description = get_ax_attribute(element, "AXDescription")
    value = get_ax_attribute(element, "AXValue")
    label = get_ax_attribute(element, "AXLabel")
    identifier = get_ax_attribute(element, "AXIdentifier")
    enabled = get_ax_attribute(element, "AXEnabled")
    position = get_ax_position(element)
    size = get_ax_size(element)

    # Convert role to string if needed
    role_str = str(role) if role else None

    # Apply filters
    if filter_type == 'buttons':
        # Only include buttons, links, and other tappable elements
        tappable_roles = ['AXButton', 'AXLink', 'AXMenuItem', 'AXCell',
                          'AXCheckBox', 'AXRadioButton', 'AXPopUpButton',
                          'AXTabButton', 'AXToggle']
        if role_str not in tappable_roles:
            # Still process children
            children = get_ax_attribute(element, "AXChildren")
            if children:
                child_results = []
                for child in children:
                    child_dict = element_to_dict(child, depth + 1, max_depth, filter_type)
                    if child_dict:
                        if isinstance(child_dict, list):
                            child_results.extend(child_dict)
                        else:
                            child_results.append(child_dict)
                return child_results if child_results else None
            return None

    if filter_type == 'text-fields':
        # Only include text input elements
        text_roles = ['AXTextField', 'AXTextArea', 'AXSearchField',
                      'AXSecureTextField', 'AXComboBox']
        if role_str not in text_roles:
            # Still process children
            children = get_ax_attribute(element, "AXChildren")
            if children:
                child_results = []
                for child in children:
                    child_dict = element_to_dict(child, depth + 1, max_depth, filter_type)
                    if child_dict:
                        if isinstance(child_dict, list):
                            child_results.extend(child_dict)
                        else:
                            child_results.append(child_dict)
                return child_results if child_results else None
            return None

    # Build result dict
    result = {}

    if role_str:
        # Simplify role names
        result['role'] = role_str.replace('AX', '')

    if subrole:
        result['subrole'] = str(subrole).replace('AX', '')

    # Use the most descriptive label available
    display_label = label or title or description or identifier
    if display_label:
        result['label'] = str(display_label)

    if value is not None and str(value):
        result['value'] = str(value)

    if enabled is not None and not enabled:
        result['enabled'] = False

    if position:
        result['position'] = position

    if size:
        result['size'] = size

    # Calculate center point for easier tapping
    if position and size:
        result['center'] = {
            'x': position['x'] + size['width'] // 2,
            'y': position['y'] + size['height'] // 2
        }

    # Process children
    children = get_ax_attribute(element, "AXChildren")
    if children and len(children) > 0:
        child_dicts = []
        for child in children:
            child_dict = element_to_dict(child, depth + 1, max_depth, filter_type)
            if child_dict:
                if isinstance(child_dict, list):
                    child_dicts.extend(child_dict)
                else:
                    child_dicts.append(child_dict)
        if child_dicts:
            result['children'] = child_dicts

    # Skip empty elements (no useful info)
    if len(result) <= 1 and 'children' not in result:
        return None

    return result


def find_simulator_window_element(app_element, device_name=None):
    """Find the simulator window element within the app."""
    windows = get_ax_attribute(app_element, "AXWindows")
    if not windows:
        return None

    for window in windows:
        title = get_ax_attribute(window, "AXTitle")
        if title:
            # If device_name specified, try to match
            if device_name:
                if device_name in str(title):
                    return window
            else:
                # Return first window that looks like a simulator
                if any(keyword in str(title) for keyword in ['iPhone', 'iPad', 'Apple Watch', 'Apple TV']):
                    return window

    # Return first window if no match
    return windows[0] if windows else None


def flatten_tappable_elements(element_tree, result=None):
    """Extract flat list of tappable elements with positions."""
    if result is None:
        result = []

    if not element_tree:
        return result

    if isinstance(element_tree, list):
        for item in element_tree:
            flatten_tappable_elements(item, result)
        return result

    role = element_tree.get('role', '')
    tappable_roles = ['Button', 'Link', 'MenuItem', 'Cell', 'CheckBox',
                      'RadioButton', 'PopUpButton', 'TabButton', 'Toggle',
                      'TextField', 'TextArea', 'SearchField', 'SecureTextField']

    if role in tappable_roles and element_tree.get('center'):
        entry = {
            'role': role,
            'center': element_tree['center']
        }
        if 'label' in element_tree:
            entry['label'] = element_tree['label']
        if 'value' in element_tree:
            entry['value'] = element_tree['value']
        result.append(entry)

    # Process children
    if 'children' in element_tree:
        flatten_tappable_elements(element_tree['children'], result)

    return result


def main():
    parser = argparse.ArgumentParser(description='Describe UI elements on iOS Simulator')
    parser.add_argument('--udid', help='Simulator UDID')
    parser.add_argument('--max-depth', type=int, default=10, help='Max traversal depth')
    parser.add_argument('--buttons', action='store_true', help='Show only tappable elements')
    parser.add_argument('--text-fields', action='store_true', help='Show only text fields')
    parser.add_argument('--all', action='store_true', help='Show all elements (verbose)')
    parser.add_argument('--flat', action='store_true', help='Flat list of tappable elements')
    args = parser.parse_args()

    if not HAS_ACCESSIBILITY:
        print(json.dumps({
            'success': False,
            'error': 'Accessibility modules not available. Requires pyobjc on macOS.'
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

    # Get Simulator.app PID
    pid = get_simulator_pid()
    if not pid:
        print(json.dumps({
            'success': False,
            'error': 'Simulator.app is not running'
        }))
        sys.exit(1)

    # Create AXUIElement for the app
    app_element = AXUIElementCreateApplication(pid)
    if not app_element:
        print(json.dumps({
            'success': False,
            'error': 'Could not access Simulator accessibility tree. Grant accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility'
        }))
        sys.exit(1)

    # Find the simulator window
    window_element = find_simulator_window_element(app_element, device_name)
    if not window_element:
        print(json.dumps({
            'success': False,
            'error': 'Could not find Simulator window'
        }))
        sys.exit(1)

    # Determine filter type
    filter_type = None
    if args.buttons:
        filter_type = 'buttons'
    elif args.text_fields:
        filter_type = 'text-fields'

    # Get element tree
    element_tree = element_to_dict(
        window_element,
        depth=0,
        max_depth=args.max_depth,
        filter_type=filter_type
    )

    if args.flat:
        # Return flat list of tappable elements
        flat_list = flatten_tappable_elements(element_tree)
        print(json.dumps({
            'success': True,
            'count': len(flat_list),
            'elements': flat_list,
            'udid': udid,
            'device': device_name
        }, indent=2))
    else:
        print(json.dumps({
            'success': True,
            'ui_tree': element_tree,
            'udid': udid,
            'device': device_name
        }, indent=2))


if __name__ == '__main__':
    main()
