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
