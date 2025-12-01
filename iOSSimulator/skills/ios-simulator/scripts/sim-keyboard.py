#!/usr/bin/env python3
"""
Send keyboard shortcuts and special keys to iOS Simulator.

Usage:
    sim-keyboard.py --key <key> [--modifiers <mod1,mod2>]

Options:
    --key <key>           Key to press (see list below)
    --modifiers <mods>    Comma-separated modifiers: cmd, shift, ctrl, alt

Special Keys:
    home        - Home button (Cmd+Shift+H)
    lock        - Lock screen (Cmd+L)
    screenshot  - Take device screenshot (Cmd+S)
    rotate-left - Rotate left (Cmd+Left)
    rotate-right - Rotate right (Cmd+Right)
    shake       - Shake gesture (Ctrl+Cmd+Z)
    keyboard    - Toggle software keyboard (Cmd+K)
    siri        - Trigger Siri (hold Home)
    app-switcher - Open App Switcher (Cmd+Shift+H twice)
    increase-size - Increase window size (Cmd+=)
    decrease-size - Decrease window size (Cmd+-)

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse
import time


def get_booted_simulator():
    """Get the first booted simulator's UDID."""
    cmd = ['xcrun', 'simctl', 'list', '-j', 'devices']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    data = json.loads(result.stdout)
    for runtime, devices in data.get('devices', {}).items():
        for device in devices:
            if device.get('state') == 'Booted':
                return device.get('udid')
    return None


def activate_simulator():
    """Bring Simulator.app to front."""
    script = 'tell application "Simulator" to activate'
    subprocess.run(['osascript', '-e', script], capture_output=True)
    time.sleep(0.1)


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


def main():
    parser = argparse.ArgumentParser(description='Send keyboard input to iOS Simulator')
    parser.add_argument('--key', '-k', help='Key or shortcut name to send')
    parser.add_argument('--modifiers', '-m', help='Comma-separated modifiers: cmd,shift,ctrl,alt')
    parser.add_argument('key_positional', nargs='?', help='Key or shortcut name')
    args = parser.parse_args()

    key = args.key or args.key_positional
    if not key:
        # List available shortcuts
        print(json.dumps({
            'success': True,
            'message': 'Available shortcuts',
            'shortcuts': list(SHORTCUTS.keys()) + ['app-switcher']
        }))
        return

    # Verify simulator is booted
    udid = get_booted_simulator()
    if not udid:
        print(json.dumps({
            'success': False,
            'error': 'No booted simulator found'
        }))
        sys.exit(1)

    # Handle special case
    if key == 'app-switcher':
        success, error = send_app_switcher()
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
            mod_map = {
                'cmd': 'command down',
                'command': 'command down',
                'shift': 'shift down',
                'ctrl': 'control down',
                'control': 'control down',
                'alt': 'option down',
                'option': 'option down'
            }
            modifiers = [mod_map.get(m.strip().lower(), m.strip() + ' down')
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
