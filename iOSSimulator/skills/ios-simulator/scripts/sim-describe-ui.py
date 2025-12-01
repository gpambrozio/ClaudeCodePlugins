#!/usr/bin/env python3
"""
Describe UI elements in the Simulator window using macOS Accessibility APIs.

Usage:
    sim-describe-ui.py [--udid <udid>] [--max-depth <depth>]

Options:
    --udid <udid>        Simulator UDID (uses booted if not specified)
    --max-depth <depth>  Maximum depth to traverse (default: 5)
    --buttons            Show only buttons and tappable elements
    --text-fields        Show only text input fields
    --flat               Flat list of labeled interactive elements

Output:
    JSON object with UI element information including:
    - role: Element type (button, text field, static text, etc.)
    - label: Element name/label
    - value: Current value (for text fields)
    - position: Screen coordinates {x, y}
    - size: Element dimensions {width, height}
    - center: Center point for clicking

Important:
    This tool accesses the SIMULATOR WINDOW's accessibility elements (window
    chrome, toolbar, device buttons like Volume/Sleep). It does NOT access
    the iOS app UI rendered inside the simulator - that requires screenshots.

    For iOS app UI elements, use sim-screenshot.py and visually identify
    coordinates from the image.

Notes:
    - Requires Accessibility permissions for Terminal/IDE
    - First run may prompt for accessibility access in System Preferences
"""

import subprocess
import json
import sys
import argparse
import re


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


def get_ui_elements_applescript(device_name=None, max_depth=5):
    """Get UI elements using AppleScript."""

    # AppleScript to extract UI elements from Simulator
    script = '''
    use framework "Foundation"
    use scripting additions

    on getElementInfo(uiElement, depth, maxDepth)
        if depth > maxDepth then return missing value

        set elementInfo to {}

        try
            set elementRole to role of uiElement
            set end of elementInfo to {"role", elementRole}
        end try

        try
            set elementName to name of uiElement
            if elementName is not missing value and elementName is not "" then
                set end of elementInfo to {"name", elementName}
            end if
        end try

        try
            set elementDesc to description of uiElement
            if elementDesc is not missing value and elementDesc is not "" then
                set end of elementInfo to {"description", elementDesc}
            end if
        end try

        try
            set elementValue to value of uiElement
            if elementValue is not missing value then
                set end of elementInfo to {"value", elementValue as text}
            end if
        end try

        try
            set elementPos to position of uiElement
            set end of elementInfo to {"position", elementPos}
        end try

        try
            set elementSize to size of uiElement
            set end of elementInfo to {"size", elementSize}
        end try

        try
            set elementEnabled to enabled of uiElement
            set end of elementInfo to {"enabled", elementEnabled}
        end try

        return elementInfo
    end getElementInfo

    on run
        set outputLines to {}

        tell application "System Events"
            tell process "Simulator"
                set frontmost to true
                delay 0.1

                try
                    set simWindow to front window
                    set windowName to name of simWindow

                    -- Get all UI elements recursively
                    set allElements to entire contents of simWindow

                    repeat with elem in allElements
                        try
                            set elemRole to role of elem
                            set elemName to ""
                            set elemDesc to ""
                            set elemValue to ""
                            set elemPos to {0, 0}
                            set elemSize to {0, 0}

                            try
                                set elemName to name of elem
                            end try
                            try
                                set elemDesc to description of elem
                            end try
                            try
                                set elemValue to value of elem as text
                            end try
                            try
                                set elemPos to position of elem
                            end try
                            try
                                set elemSize to size of elem
                            end try

                            -- Format: role|name|description|value|posX|posY|sizeW|sizeH
                            set elemLine to elemRole & "|" & elemName & "|" & elemDesc & "|" & elemValue & "|" & (item 1 of elemPos) & "|" & (item 2 of elemPos) & "|" & (item 1 of elemSize) & "|" & (item 2 of elemSize)
                            set end of outputLines to elemLine
                        end try
                    end repeat

                on error errMsg
                    return "ERROR:" & errMsg
                end try
            end tell
        end tell

        -- Join lines with newline
        set AppleScript's text item delimiters to linefeed
        return outputLines as text
    end run
    '''

    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        return None, result.stderr

    return result.stdout, None


def parse_applescript_output(output, filter_type=None):
    """Parse AppleScript output into structured data."""
    elements = []

    if not output or output.startswith("ERROR:"):
        return elements

    # Tappable roles for filtering
    tappable_roles = [
        'AXButton', 'button',
        'AXLink', 'link',
        'AXMenuItem', 'menu item',
        'AXCell', 'cell',
        'AXCheckBox', 'checkbox',
        'AXRadioButton', 'radio button',
        'AXPopUpButton', 'pop up button',
        'AXStaticText', 'static text',
        'AXImage', 'image',
        'AXGroup', 'group'
    ]

    text_roles = [
        'AXTextField', 'text field',
        'AXTextArea', 'text area',
        'AXSearchField', 'search field',
        'AXSecureTextField', 'secure text field',
        'AXComboBox', 'combo box'
    ]

    for line in output.strip().split('\n'):
        if not line or '|' not in line:
            continue

        parts = line.split('|')
        if len(parts) < 8:
            continue

        role = parts[0].strip()
        name = parts[1].strip()
        desc = parts[2].strip()
        value = parts[3].strip()

        try:
            pos_x = int(float(parts[4]))
            pos_y = int(float(parts[5]))
            size_w = int(float(parts[6]))
            size_h = int(float(parts[7]))
        except (ValueError, IndexError):
            continue

        # Skip elements with no position or size
        if size_w == 0 and size_h == 0:
            continue

        # Apply filters
        role_lower = role.lower()
        if filter_type == 'buttons':
            if not any(r.lower() in role_lower for r in tappable_roles):
                continue
        elif filter_type == 'text-fields':
            if not any(r.lower() in role_lower for r in text_roles):
                continue

        element = {
            'role': role.replace('AX', ''),
            'position': {'x': pos_x, 'y': pos_y},
            'size': {'width': size_w, 'height': size_h},
            'center': {
                'x': pos_x + size_w // 2,
                'y': pos_y + size_h // 2
            }
        }

        # Add optional fields
        label = name or desc
        if label and label != 'missing value':
            element['label'] = label
        if value and value != 'missing value':
            element['value'] = value

        elements.append(element)

    return elements


def flatten_for_tapping(elements):
    """Filter to just interactive elements with useful info."""
    interactive_roles = [
        'button', 'link', 'menuitem', 'cell', 'checkbox',
        'radiobutton', 'popupbutton', 'textfield', 'textarea',
        'searchfield', 'securetextfield', 'combobox', 'slider',
        'incrementor', 'statictext', 'image'
    ]

    result = []
    seen_positions = set()

    for elem in elements:
        role_lower = elem.get('role', '').lower().replace(' ', '')
        label = elem.get('label', '')

        # Skip "missing value" labels
        if label == 'missing value':
            label = ''

        # Include if it has a real label or is clearly interactive
        has_label = bool(label)
        is_interactive = any(r in role_lower for r in interactive_roles)

        if has_label:
            # Dedupe by position
            pos_key = (elem['center']['x'], elem['center']['y'])
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                result.append({
                    'role': elem['role'],
                    'label': label,
                    'center': elem['center']
                })

    return result


def main():
    parser = argparse.ArgumentParser(description='Describe UI elements on iOS Simulator')
    parser.add_argument('--udid', help='Simulator UDID')
    parser.add_argument('--max-depth', type=int, default=5, help='Max traversal depth')
    parser.add_argument('--buttons', action='store_true', help='Show only tappable elements')
    parser.add_argument('--text-fields', action='store_true', help='Show only text fields')
    parser.add_argument('--flat', action='store_true', help='Flat list of interactive elements')
    args = parser.parse_args()

    # Get booted simulator
    udid, device_name = get_booted_simulator()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    # Get UI elements via AppleScript
    output, error = get_ui_elements_applescript(device_name, args.max_depth)

    if error:
        print(json.dumps({
            'success': False,
            'error': f'AppleScript error: {error.strip()}',
            'hint': 'Grant accessibility permissions in System Settings > Privacy & Security > Accessibility'
        }))
        sys.exit(1)

    if not output or output.startswith("ERROR:"):
        error_msg = output.replace("ERROR:", "") if output else "No output"
        print(json.dumps({
            'success': False,
            'error': f'Could not get UI elements: {error_msg}',
            'hint': 'Grant accessibility permissions in System Settings > Privacy & Security > Accessibility'
        }))
        sys.exit(1)

    # Determine filter type
    filter_type = None
    if args.buttons:
        filter_type = 'buttons'
    elif args.text_fields:
        filter_type = 'text-fields'

    # Parse elements
    elements = parse_applescript_output(output, filter_type)

    if args.flat:
        # Return simplified flat list
        flat_list = flatten_for_tapping(elements)
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
            'count': len(elements),
            'elements': elements,
            'udid': udid,
            'device': device_name
        }, indent=2))


if __name__ == '__main__':
    main()
