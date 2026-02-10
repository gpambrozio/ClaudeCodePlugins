#!/usr/bin/env python3
"""
Analyze the current simulator screen and categorize UI elements.

Provides a token-efficient summary of what's on screen without
requiring the agent to parse the full accessibility tree.

Usage:
    sim-screen-map.py [--udid <udid>] [--verbose] [--hints]

Options:
    --udid <udid>       Simulator UDID (uses booted if not specified)
    --verbose           Show detailed element breakdown by type
    --hints             Include navigation hints based on screen analysis

Output:
    JSON object with element counts, categories, and interactive elements.

Notes:
    - Requires uv (same as sim-describe-ui.py)
    - Uses sim-describe-ui.py internally to read the accessibility tree
    - Designed for AI agents making navigation decisions
"""

import json
import subprocess
import sys
import os
import argparse

from sim_utils import get_booted_simulator_udid

# AXRoles that are interactive
INTERACTIVE_ROLES = {
    'AXButton', 'AXLink', 'AXTextField', 'AXSecureTextField',
    'AXCell', 'AXSwitch', 'AXSlider', 'AXStepper',
    'AXSegmentedControl', 'AXPopUpButton', 'AXComboBox',
    'AXCheckBox', 'AXRadioButton', 'AXMenuItem',
}

# AXRoles that are navigation structures
NAVIGATION_ROLES = {
    'AXNavigationBar', 'AXTabBar', 'AXToolbar', 'AXMenuBar',
}


def get_flat_elements(udid=None):
    """Get the flat element list from sim-describe-ui.py.

    Returns:
        Tuple of (elements_list, error_string)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    describe_script = os.path.join(script_dir, 'sim-describe-ui.py')

    cmd = [describe_script, '--format', 'flat']
    if udid:
        cmd.extend(['--udid', udid])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            # Try to parse error from JSON output
            try:
                data = json.loads(result.stdout)
                return None, data.get('error', 'sim-describe-ui.py failed')
            except (json.JSONDecodeError, KeyError):
                return None, result.stderr.strip() or 'sim-describe-ui.py failed'

        data = json.loads(result.stdout)
        if not data.get('success'):
            return None, data.get('error', 'Failed to get UI tree')

        return data.get('elements', []), None

    except subprocess.TimeoutExpired:
        return None, 'sim-describe-ui.py timed out'
    except json.JSONDecodeError:
        return None, 'Invalid JSON from sim-describe-ui.py'
    except FileNotFoundError:
        return None, f'sim-describe-ui.py not found at {describe_script}'


def analyze_elements(elements):
    """Analyze a flat list of accessibility elements.

    Returns:
        Analysis dict with counts, categories, and details.
    """
    by_role = {}
    buttons = []
    text_fields = []
    nav_info = {}
    interactive_count = 0
    total = len(elements)

    for elem in elements:
        role = elem.get('AXRole', '')
        label = (elem.get('AXLabel') or elem.get('AXTitle')
                 or elem.get('AXDescription') or '')
        value = elem.get('AXValue', '')
        identifier = elem.get('AXIdentifier', '')

        # Count by role
        by_role[role] = by_role.get(role, 0) + 1

        # Track interactive elements
        if role in INTERACTIVE_ROLES:
            interactive_count += 1

        # Collect buttons with labels
        if role == 'AXButton' and label:
            buttons.append(label)

        # Collect text fields
        if role in ('AXTextField', 'AXSecureTextField'):
            text_fields.append({
                'label': label or identifier or 'Unnamed',
                'type': 'secure' if role == 'AXSecureTextField' else 'text',
                'has_value': bool(value),
            })

        # Detect navigation structures
        if role in NAVIGATION_ROLES:
            if role == 'AXNavigationBar' and label:
                nav_info['nav_title'] = label
            elif role == 'AXTabBar':
                nav_info['has_tab_bar'] = True

    return {
        'total_elements': total,
        'interactive_elements': interactive_count,
        'buttons': buttons,
        'text_fields': text_fields,
        'navigation': nav_info,
        'roles': by_role,
    }


def build_hints(analysis):
    """Generate navigation hints based on screen analysis."""
    hints = []
    buttons_lower = [b.lower() for b in analysis['buttons']]

    if any(w in buttons_lower for w in ['login', 'sign in', 'log in']):
        hints.append('Login screen detected - look for text fields for credentials')

    unfilled = [f for f in analysis['text_fields'] if not f['has_value']]
    if unfilled:
        hints.append(f'{len(unfilled)} empty text field(s) may need input')

    if analysis['interactive_elements'] == 0:
        hints.append('No interactive elements visible - try scrolling or navigating back')

    if analysis['navigation'].get('has_tab_bar'):
        hints.append('Tab bar present - can switch between app sections')

    return hints


def main():
    parser = argparse.ArgumentParser(description='Analyze current simulator screen elements')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('--verbose', action='store_true', help='Show element breakdown by role')
    parser.add_argument('--hints', action='store_true', help='Include navigation hints')

    args = parser.parse_args()

    # Resolve UDID
    udid = args.udid
    if not udid:
        udid = get_booted_simulator_udid()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    # Get elements
    elements, error = get_flat_elements(udid)
    if error:
        print(json.dumps({'success': False, 'error': error}))
        sys.exit(1)

    # Analyze
    analysis = analyze_elements(elements)

    result = {
        'success': True,
        'udid': udid,
        'total_elements': analysis['total_elements'],
        'interactive_elements': analysis['interactive_elements'],
        'buttons': analysis['buttons'][:10],
        'text_fields': analysis['text_fields'],
        'navigation': analysis['navigation'],
    }

    if len(analysis['buttons']) > 10:
        result['buttons_truncated'] = len(analysis['buttons'])

    if args.verbose:
        result['roles'] = analysis['roles']

    if args.hints:
        result['hints'] = build_hints(analysis)

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
