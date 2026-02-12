#!/usr/bin/env python3
"""
Shared utilities for iOS Simulator scripts.

This module contains common functions used across multiple sim-*.py scripts
to reduce code duplication and ensure consistent behavior.
"""

import subprocess
import json
import time
from contextlib import contextmanager
from typing import Optional, Tuple

# Quartz window detection (macOS-only, used by sim-tap and sim-swipe)
try:
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False

# Simulator window chrome offsets (Point Accurate mode)
TITLE_BAR_HEIGHT = 28
DEVICE_TOP_BEZEL = 50
LEFT_BEZEL = 20
RIGHT_BEZEL = 20
BOTTOM_BEZEL = 50


def run_simctl(*args) -> Tuple[bool, str, str]:
    """
    Run xcrun simctl command and return result.

    Args:
        *args: Arguments to pass to simctl

    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    cmd = ['xcrun', 'simctl'] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def get_simulators() -> Tuple[Optional[dict], Optional[str]]:
    """
    Get all simulators as JSON.

    Returns:
        Tuple of (devices_data: dict, error: str or None)
    """
    success, stdout, stderr = run_simctl('list', '-j', 'devices')
    if not success:
        return None, stderr
    return json.loads(stdout), None


def get_booted_simulator() -> Tuple[Optional[str], Optional[str]]:
    """
    Get the first booted simulator's UDID and name.

    Returns:
        Tuple of (udid: str or None, name: str or None)
    """
    success, stdout, stderr = run_simctl('list', '-j', 'devices')
    if not success:
        return None, None

    data = json.loads(stdout)
    for runtime, devices in data.get('devices', {}).items():
        for device in devices:
            if device.get('state') == 'Booted':
                return device.get('udid'), device.get('name')
    return None, None


def get_booted_simulator_udid() -> Optional[str]:
    """
    Get just the UDID of the first booted simulator.

    Convenience function for scripts that only need the UDID.

    Returns:
        UDID string or None if no simulator is booted
    """
    udid, _ = get_booted_simulator()
    return udid


def find_simulator_by_name(name: str, runtime: Optional[str] = None) -> Optional[dict]:
    """
    Find a simulator by name, optionally filtered by runtime.

    Args:
        name: Simulator name (e.g., "iPhone 15")
        runtime: Optional runtime filter (e.g., "iOS-17")

    Returns:
        Dict with simulator info or None if not found
    """
    devices_data, error = get_simulators()
    if not devices_data:
        return None

    matches = []
    for rt, devices in devices_data.get('devices', {}).items():
        if runtime and runtime not in rt:
            continue
        for device in devices:
            if device.get('name') == name and device.get('isAvailable', True):
                matches.append({
                    'udid': device.get('udid'),
                    'name': device.get('name'),
                    'state': device.get('state'),
                    'runtime': rt.split('.')[-1]
                })

    # Return the first match, preferring newer runtimes (sorted desc)
    if matches:
        matches.sort(key=lambda x: x['runtime'], reverse=True)
        return matches[0]
    return None


def open_simulator_app() -> None:
    """Open the Simulator.app to show the booted simulator.

    Uses -g flag to open in background without stealing focus.
    """
    subprocess.run(['open', '-g', '-a', 'Simulator'], capture_output=True)


def get_simulator_window_info(device_name=None):
    """Get Simulator window position and size.

    On macOS 26.3+, kCGWindowName is always empty for non-system apps
    (privacy hardening), so we match by owner name only and pick the
    largest Simulator window by area. The device_name parameter is kept
    for backward compatibility but is no longer used for matching.
    """
    if not HAS_QUARTZ:
        return None

    window_list = CGWindowListCopyWindowInfo(
        kCGWindowListOptionOnScreenOnly, kCGNullWindowID
    )

    candidates = []
    for window in window_list:
        owner = window.get('kCGWindowOwnerName', '')
        if owner != 'Simulator':
            continue

        bounds = window.get('kCGWindowBounds', {})
        width = bounds.get('Width', 0)
        height = bounds.get('Height', 0)

        # Skip small windows (menu bars, toolbars, floating panels)
        if width < 100 or height < 100:
            continue

        candidates.append({
            'x': bounds.get('X', 0),
            'y': bounds.get('Y', 0),
            'width': width,
            'height': height,
            'name': window.get('kCGWindowName', ''),
            'area': width * height,
        })

    if not candidates:
        return None

    # Pick the largest window (the device window is always biggest)
    best = max(candidates, key=lambda w: w['area'])
    del best['area']
    return best


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


def activate_simulator(point_accurate=False):
    """Bring Simulator.app to front.

    Args:
        point_accurate: If True, also switch to Point Accurate mode (Cmd+2).
                       Used by sim-tap and sim-swipe for correct coordinate mapping.
    """
    if point_accurate:
        set_point_accurate_mode()
    else:
        script = 'tell application "Simulator" to activate'
        subprocess.run(['osascript', '-e', script], capture_output=True)
        time.sleep(0.1)


def screen_to_window_coords(screen_x, screen_y, window_info):
    """Convert simulator screen coordinates to window coordinates.

    Takes screen-point coordinates (as shown in the simulator UI) and
    converts them to absolute window coordinates for Quartz mouse events.
    """
    window_x = window_info['x'] + screen_x + LEFT_BEZEL
    window_y = window_info['y'] + TITLE_BAR_HEIGHT + DEVICE_TOP_BEZEL + screen_y
    return window_x, window_y


def get_screen_size_from_window(window_info):
    """Estimate the iOS screen size from the simulator window dimensions."""
    width = window_info['width'] - LEFT_BEZEL - RIGHT_BEZEL
    height = window_info['height'] - TITLE_BAR_HEIGHT - DEVICE_TOP_BEZEL - BOTTOM_BEZEL

    if width > 0 and height > 0:
        return width, height
    return 390, 700  # fallback


def get_frontmost_app():
    """Get the name of the current frontmost application."""
    result = subprocess.run(
        ['osascript', '-e',
         'tell application "System Events" to get name of first process whose frontmost is true'],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def restore_frontmost_app(app_name):
    """Restore the previously frontmost application."""
    if app_name and app_name != 'Simulator':
        subprocess.run(
            ['osascript', '-e', f'tell application "{app_name}" to activate'],
            capture_output=True,
        )


@contextmanager
def preserve_focus():
    """Context manager: saves frontmost app, yields, then restores it."""
    previous_app = get_frontmost_app()
    try:
        yield
    finally:
        restore_frontmost_app(previous_app)


# Common simctl error patterns and their handling
# Format: (pattern, category, is_non_error, hint)
SIMCTL_ERROR_PATTERNS = [
    # Boot errors
    ('Unable to boot device in current state: Booted', 'already_booted', True,
     'The simulator is already running.'),
    ('Unable to boot device in current state: Shutdown', 'boot_failed', False,
     'Try resetting the simulator with "xcrun simctl erase".'),

    # Shutdown errors
    ('current state: Shutdown', 'already_shutdown', True,
     'The simulator is already shut down.'),

    # Invalid device errors (multiple patterns)
    ('Invalid device or device pair', 'invalid_device', False,
     'Check available devices with sim-list.py.'),
    ('Invalid device:', 'invalid_device', False,
     'Check available devices with sim-list.py.'),

    # App lifecycle errors
    ('Invalid bundle identifier', 'invalid_bundle', False,
     'The app may not be installed. Install it first with sim-install.py.'),
    ('The application with bundle identifier', 'app_not_found', False,
     'The app is not installed. Install it first with sim-install.py.'),
    ('The request to open', 'app_not_found', False,
     'The app may not be installed. Install it first with sim-install.py.'),
    ('failed to launch', 'launch_failed', False,
     'The app failed to launch. Verify it is installed with sim-list.py.'),
    ('No matching processes belonging to', 'app_not_running', True,
     'The app is not currently running.'),
    ('found nothing to terminate', 'app_not_running', True,
     'The app is not currently running.'),

    # Install errors
    ('Unable to install', 'install_failed', False,
     'Check that the .app bundle is valid and built for the simulator.'),
    ('MismatchedApplicationIdentifierEntitlement', 'bundle_conflict', False,
     'An app with the same bundle ID but different signing exists. Uninstall it first.'),

    # URL errors
    ('The request was denied by service delegate', 'url_denied', False,
     'The URL scheme may not be registered or the app is not installed.'),

    # Location errors
    ('Unable to set location', 'location_failed', False,
     'Ensure the simulator is fully booted and try again.'),

    # Screenshot errors
    ('Could not complete request', 'screenshot_failed', False,
     'Ensure the simulator is fully booted and visible.'),

    # General errors
    ('Device not found', 'device_not_found', False,
     'The specified simulator UDID does not exist. Check sim-list.py.'),
    ('Simulator is not running', 'not_running', False,
     'Boot the simulator first with sim-boot.py.'),
    ('Unable to lookup in current state: Shutdown', 'not_booted', False,
     'The simulator must be booted first with sim-boot.py.'),
    ('Timed out', 'timeout', False,
     'The operation timed out. The simulator may be overloaded.'),
]


class SimctlError:
    """Parsed simctl error with category and hints."""

    def __init__(self, raw_error: str, category: str = 'unknown',
                 is_non_error: bool = False, hint: Optional[str] = None):
        self.raw_error = raw_error.strip() if raw_error else ''
        self.category = category
        self.is_non_error = is_non_error
        self.hint = hint

    def get_message(self) -> str:
        """Get a user-friendly error message with hint if available."""
        if self.hint and self.hint not in self.raw_error:
            return f"{self.raw_error} {self.hint}"
        return self.raw_error

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        result = {
            'error': self.get_message(),
            'category': self.category,
        }
        if self.is_non_error:
            result['is_non_error'] = True
        return result


def parse_simctl_error(stderr: str) -> SimctlError:
    """
    Parse a simctl error message and return structured error info.

    This provides consistent error handling across all sim-*.py scripts by:
    - Categorizing known error patterns
    - Identifying non-error conditions (already booted, etc.)
    - Adding helpful hints for common problems

    Args:
        stderr: The stderr output from a simctl command

    Returns:
        SimctlError with parsed information
    """
    if not stderr:
        return SimctlError('Unknown error occurred', 'unknown')

    stderr_clean = stderr.strip()

    for pattern, category, is_non_error, hint in SIMCTL_ERROR_PATTERNS:
        if pattern in stderr_clean:
            return SimctlError(stderr_clean, category, is_non_error, hint)

    # No pattern matched - return with unknown category
    return SimctlError(stderr_clean, 'unknown')


def handle_simctl_result(success: bool, stderr: str, operation: str = 'operation',
                         context: Optional[dict] = None) -> Tuple[bool, dict]:
    """
    Handle a simctl command result and return a standardized response.

    This is the main entry point for consistent error handling. It returns
    a tuple of (actual_success, response_dict) where actual_success accounts
    for non-error conditions like "already booted".

    Args:
        success: Whether the simctl command returned exit code 0
        stderr: The stderr output from the command
        operation: Description of the operation for error messages
        context: Additional context to include in error responses

    Returns:
        Tuple of (actual_success: bool, response: dict)
        - actual_success is True if command succeeded OR if error was a non-error
        - response is a dict ready for JSON output
    """
    if success:
        return True, {}

    error = parse_simctl_error(stderr)

    if error.is_non_error:
        # This is a "success" condition (e.g., already booted)
        return True, {
            'success': True,
            'message': error.hint or f'{operation} already complete',
            'note': error.raw_error
        }

    # Actual error
    response = {
        'success': False,
        'error': error.get_message(),
        'error_category': error.category,
    }
    if context:
        response.update(context)

    return False, response
