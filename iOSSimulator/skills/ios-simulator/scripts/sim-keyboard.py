#!/usr/bin/env python3
"""
Send keyboard shortcuts and special keys to iOS Simulator.

Usage:
    sim-keyboard.py --key <key> [--modifiers <mod1,mod2>]
    sim-keyboard.py --combo <combo>
    sim-keyboard.py --clear
    sim-keyboard.py --dismiss

Options:
    --key <key>           Key to press (see list below)
    --modifiers <mods>    Comma-separated modifiers: cmd, shift, ctrl, alt
    --combo <combo>       Key combination (e.g., cmd+a, cmd+shift+h, ctrl+cmd+z)
    --clear               Clear current text field (Cmd+A then Delete)
    --dismiss             Dismiss the software keyboard (Cmd+K)
    --udid <udid>         Simulator UDID (uses booted if not specified)

Special Keys:
    home         - Home button (Cmd+Shift+H)
    lock         - Lock screen (Cmd+L)
    screenshot   - Take device screenshot (Cmd+S)
    rotate-left  - Rotate left (Cmd+Left)
    rotate-right - Rotate right (Cmd+Right)
    shake        - Shake gesture (Ctrl+Cmd+Z)
    keyboard     - Toggle software keyboard (Cmd+K)
    siri         - Trigger Siri (hold Home)
    app-switcher - Open App Switcher (Cmd+Shift+H twice)
    increase-size - Increase window size (Cmd+=)
    decrease-size - Decrease window size (Cmd+-)
    volume-up    - Increase volume
    volume-down  - Decrease volume
    ringer       - Toggle ringer/mute

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse
import time

from sim_utils import get_booted_simulator_udid, activate_simulator, preserve_focus


# Predefined shortcuts
SHORTCUTS = {
    'home': {'key': 'h', 'modifiers': ['command down', 'shift down']},
    'lock': {'key': 'l', 'modifiers': ['command down']},
    'screenshot': {'key': 's', 'modifiers': ['command down']},
    'rotate-left': {'key': '123', 'modifiers': ['command down'], 'keycode': True},  # Left arrow
    'rotate-right': {'key': '124', 'modifiers': ['command down'], 'keycode': True},  # Right arrow
    'shake': {'key': 'z', 'modifiers': ['control down', 'command down']},
    'keyboard': {'key': 'k', 'modifiers': ['command down']},
    'increase-size': {'key': '=', 'modifiers': ['command down']},
    'decrease-size': {'key': '-', 'modifiers': ['command down']},
}

# Modifier name to AppleScript modifier mapping
MODIFIER_MAP = {
    'cmd': 'command down',
    'command': 'command down',
    'shift': 'shift down',
    'ctrl': 'control down',
    'control': 'control down',
    'alt': 'option down',
    'option': 'option down',
}

# AppleScript key code names for special keys used in combos
KEY_CODE_MAP = {
    'left': '123',
    'right': '124',
    'down': '125',
    'up': '126',
    'delete': '51',
    'forwarddelete': '117',
    'return': '36',
    'enter': '76',
    'tab': '48',
    'escape': '53',
    'space': '49',
}


def send_keystroke(key, modifiers=None, use_keycode=False):
    """Send keystroke using AppleScript."""
    activate_simulator()

    if modifiers:
        mod_str = '{' + ', '.join(modifiers) + '}'
        if use_keycode:
            script = f'''
            tell application "System Events"
                key code {key} using {mod_str}
            end tell
            '''
        else:
            script = f'''
            tell application "System Events"
                keystroke "{key}" using {mod_str}
            end tell
            '''
    else:
        if use_keycode:
            script = f'''
            tell application "System Events"
                key code {key}
            end tell
            '''
        else:
            script = f'''
            tell application "System Events"
                keystroke "{key}"
            end tell
            '''

    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def send_app_switcher():
    """Double-press Home for App Switcher."""
    activate_simulator()
    script = '''
    tell application "System Events"
        keystroke "h" using {command down, shift down}
        delay 0.1
        keystroke "h" using {command down, shift down}
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def send_combo(combo_str):
    """Send a key combination like 'cmd+a', 'cmd+shift+h', 'ctrl+cmd+z'.

    Parses the combo string, identifies modifiers and the final key,
    then sends via AppleScript keystroke or key code as appropriate.
    """
    parts = [p.strip().lower() for p in combo_str.split('+')]
    if len(parts) < 2:
        return False, 'Combo must have at least a modifier and a key (e.g., cmd+a)'

    modifiers = []
    key_part = None

    for part in parts:
        if part in MODIFIER_MAP:
            modifiers.append(MODIFIER_MAP[part])
        else:
            key_part = part

    if not key_part:
        return False, 'No key found in combo — all parts are modifiers'
    if not modifiers:
        return False, 'No modifiers found in combo'

    # Determine if we need key code or keystroke
    use_keycode = key_part in KEY_CODE_MAP

    if use_keycode:
        key_value = KEY_CODE_MAP[key_part]
    else:
        key_value = key_part

    return send_keystroke(key_value, modifiers, use_keycode)


def clear_text_field():
    """Clear text in the focused field by selecting all then deleting."""
    activate_simulator()
    script = '''
    tell application "System Events"
        keystroke "a" using {command down}
        delay 0.1
        key code 51
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def send_hardware_button(button):
    """Send a hardware button via Simulator's Device menu using AppleScript."""
    menu_items = {
        'volume-up': 'Volume Up',
        'volume-down': 'Volume Down',
        'ringer': 'Toggle Mute',
    }

    menu_name = menu_items.get(button)
    if not menu_name:
        return False, f'Unknown hardware button: {button}'

    activate_simulator()
    script = f'''
    tell application "System Events"
        tell process "Simulator"
            click menu item "{menu_name}" of menu "Device" of menu bar 1
        end tell
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def main():
    parser = argparse.ArgumentParser(description='Send keyboard input to iOS Simulator')
    parser.add_argument('--key', '-k', help='Key or shortcut name to send')
    parser.add_argument('--modifiers', '-m', help='Comma-separated modifiers: cmd,shift,ctrl,alt')
    parser.add_argument('--combo', help='Key combination (e.g., cmd+a, cmd+shift+h, ctrl+cmd+z)')
    parser.add_argument('--clear', action='store_true',
                        help='Clear current text field (Cmd+A then Delete)')
    parser.add_argument('--dismiss', action='store_true',
                        help='Dismiss the software keyboard (Cmd+K)')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('key_positional', nargs='?', help='Key or shortcut name')
    args = parser.parse_args()

    # Verify simulator is booted
    udid = args.udid or get_booted_simulator_udid()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    with preserve_focus():
        # --- Clear text field ---
        if args.clear:
            success, error = clear_text_field()
            if success:
                print(json.dumps({
                    'success': True,
                    'message': 'Cleared text field',
                    'action': 'clear',
                    'udid': udid
                }))
            else:
                print(json.dumps({
                    'success': False,
                    'error': error.strip() if error else 'Failed to clear text field'
                }))
                sys.exit(1)
            return

        # --- Dismiss keyboard ---
        if args.dismiss:
            shortcut = SHORTCUTS['keyboard']
            success, error = send_keystroke(
                shortcut['key'], shortcut.get('modifiers'))
            if success:
                print(json.dumps({
                    'success': True,
                    'message': 'Toggled software keyboard',
                    'action': 'dismiss',
                    'udid': udid
                }))
            else:
                print(json.dumps({
                    'success': False,
                    'error': error.strip() if error else 'Failed to dismiss keyboard'
                }))
                sys.exit(1)
            return

        # --- Key combo ---
        if args.combo:
            success, error = send_combo(args.combo)
            if success:
                print(json.dumps({
                    'success': True,
                    'message': f'Sent combo: {args.combo}',
                    'combo': args.combo,
                    'udid': udid
                }))
            else:
                print(json.dumps({
                    'success': False,
                    'error': error.strip() if error else f'Failed to send combo: {args.combo}'
                }))
                sys.exit(1)
            return

        # --- Named key or shortcut ---
        key = args.key or args.key_positional
        if not key:
            # List available shortcuts
            all_keys = list(SHORTCUTS.keys()) + ['app-switcher', 'volume-up', 'volume-down', 'ringer']
            print(json.dumps({
                'success': True,
                'message': 'Available shortcuts',
                'shortcuts': all_keys
            }))
            return

        # Handle special cases
        if key == 'app-switcher':
            success, error = send_app_switcher()
        elif key in ('volume-up', 'volume-down', 'ringer'):
            success, error = send_hardware_button(key)
        elif key in SHORTCUTS:
            shortcut = SHORTCUTS[key]
            success, error = send_keystroke(
                shortcut['key'],
                shortcut.get('modifiers'),
                shortcut.get('keycode', False)
            )
        else:
            # Custom key with optional modifiers
            modifiers = None
            if args.modifiers:
                modifiers = [MODIFIER_MAP.get(m.strip().lower(), m.strip() + ' down')
                             for m in args.modifiers.split(',')]

            success, error = send_keystroke(key, modifiers)

        if success:
            print(json.dumps({
                'success': True,
                'message': f'Sent key: {key}',
                'key': key,
                'udid': udid
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': error.strip() if error else 'Failed to send keystroke'
            }))
            sys.exit(1)


if __name__ == '__main__':
    main()
