#!/usr/bin/env python3
"""
Shared utilities for iOS Simulator scripts.

This module contains common functions used across multiple sim-*.py scripts
to reduce code duplication and ensure consistent behavior.
"""

import subprocess
import json
from typing import Optional, Tuple


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
    """Open the Simulator.app to show the booted simulator."""
    subprocess.run(['open', '-a', 'Simulator'], capture_output=True)


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
