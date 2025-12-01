#!/usr/bin/env python3
"""
List available iOS Simulators with their status.

Usage:
    sim-list.py [--booted] [--available]

Options:
    --booted     Show only booted simulators
    --available  Show only available (not unavailable) simulators

Output:
    JSON object with simulators grouped by runtime, or flat list if --booted
"""

import subprocess
import json
import sys
import argparse


def run_simctl(*args):
    """Run xcrun simctl command and return output."""
    cmd = ['xcrun', 'simctl'] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout, None


def get_simulators():
    """Get all simulators as JSON."""
    output, error = run_simctl('list', '-j', 'devices')
    if error:
        return None, error
    return json.loads(output), None


def filter_booted(devices_data):
    """Extract only booted simulators as a flat list."""
    booted = []
    for runtime, devices in devices_data.get('devices', {}).items():
        # Extract iOS version from runtime string
        # e.g., "com.apple.CoreSimulator.SimRuntime.iOS-17-0" -> "iOS 17.0"
        runtime_name = runtime.split('.')[-1].replace('-', ' ').replace('iOS ', 'iOS ')

        for device in devices:
            if device.get('state') == 'Booted':
                booted.append({
                    'name': device.get('name'),
                    'udid': device.get('udid'),
                    'state': device.get('state'),
                    'runtime': runtime_name,
                    'isAvailable': device.get('isAvailable', True)
                })
    return booted


def filter_available(devices_data):
    """Filter to only available simulators."""
    filtered = {'devices': {}}
    for runtime, devices in devices_data.get('devices', {}).items():
        available_devices = [d for d in devices if d.get('isAvailable', True)]
        if available_devices:
            filtered['devices'][runtime] = available_devices
    return filtered


def simplify_output(devices_data):
    """Simplify the output for easier reading."""
    simplified = []
    for runtime, devices in devices_data.get('devices', {}).items():
        # Extract runtime name
        runtime_name = runtime.split('.')[-1].replace('-', '.').replace('iOS.', 'iOS ')

        for device in devices:
            if device.get('isAvailable', True):
                simplified.append({
                    'name': device.get('name'),
                    'udid': device.get('udid'),
                    'state': device.get('state'),
                    'runtime': runtime_name
                })
    return simplified


def main():
    parser = argparse.ArgumentParser(description='List iOS Simulators')
    parser.add_argument('--booted', action='store_true', help='Show only booted simulators')
    parser.add_argument('--available', action='store_true', help='Show only available simulators')
    parser.add_argument('--raw', action='store_true', help='Show raw simctl output')
    args = parser.parse_args()

    devices_data, error = get_simulators()

    if error:
        print(json.dumps({
            'success': False,
            'error': error.strip()
        }))
        sys.exit(1)

    if args.raw:
        print(json.dumps(devices_data, indent=2))
        return

    if args.booted:
        result = filter_booted(devices_data)
        print(json.dumps({
            'success': True,
            'count': len(result),
            'simulators': result
        }, indent=2))
        return

    if args.available:
        devices_data = filter_available(devices_data)

    # Simplify output by default
    result = simplify_output(devices_data)
    print(json.dumps({
        'success': True,
        'count': len(result),
        'simulators': result
    }, indent=2))


if __name__ == '__main__':
    main()
