#!/usr/bin/env python3
"""
Diagnose Xcode development environment and report issues.

Usage:
    xc-doctor.py [--verbose]

Options:
    --verbose    Show detailed information

Output:
    JSON object with environment diagnostics
"""

import json
import sys
import argparse
import os
import platform

from xc_utils import (
    run_command, run_xcrun, get_xcode_path, get_xcode_version,
    get_macos_version, get_available_platforms, get_derived_data_path,
    success_response, error_response
)


def check_xcode_cli_tools() -> dict:
    """Check if Xcode Command Line Tools are installed."""
    success, stdout, stderr = run_command(['xcode-select', '-p'])
    if success:
        return {
            'installed': True,
            'path': stdout.strip()
        }
    return {
        'installed': False,
        'hint': 'Install with: xcode-select --install'
    }


def check_xcode() -> dict:
    """Check Xcode installation."""
    version_info = get_xcode_version()
    if version_info:
        xcode_path = get_xcode_path()
        return {
            'installed': True,
            'version': version_info.get('xcode'),
            'build': version_info.get('build'),
            'path': xcode_path
        }
    return {
        'installed': False,
        'hint': 'Install Xcode from the App Store'
    }


def check_simulators() -> dict:
    """Check available simulators."""
    success, stdout, stderr = run_xcrun('simctl', 'list', 'devices', '-j')
    if not success:
        return {
            'available': False,
            'error': stderr.strip()
        }

    try:
        data = json.loads(stdout)
        devices = data.get('devices', {})

        available_count = 0
        booted_count = 0
        runtimes = set()

        for runtime, device_list in devices.items():
            for device in device_list:
                if device.get('isAvailable', True):
                    available_count += 1
                    # Extract runtime name
                    runtime_name = runtime.split('.')[-1].replace('-', ' ')
                    runtimes.add(runtime_name)
                    if device.get('state') == 'Booted':
                        booted_count += 1

        return {
            'available': True,
            'count': available_count,
            'booted': booted_count,
            'runtimes': sorted(runtimes)
        }
    except json.JSONDecodeError:
        return {
            'available': False,
            'error': 'Failed to parse simulator list'
        }


def check_devices() -> dict:
    """Check connected devices."""
    success, stdout, stderr = run_xcrun('xctrace', 'list', 'devices')
    if not success:
        return {
            'available': False,
            'error': stderr.strip()
        }

    # Count devices (excluding simulators)
    device_count = 0
    for line in stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('==') and 'Simulator' not in line:
            # Check if it looks like a device entry
            if '(' in line and ')' in line:
                device_count += 1

    return {
        'available': True,
        'connected_count': device_count
    }


def check_swift() -> dict:
    """Check Swift installation."""
    success, stdout, stderr = run_command(['swift', '--version'])
    if success:
        # Parse version from output
        version = None
        for line in stdout.split('\n'):
            if 'Swift version' in line:
                version = line.strip()
                break
        return {
            'installed': True,
            'version': version
        }
    return {
        'installed': False,
        'hint': 'Swift is included with Xcode'
    }


def check_cocoapods() -> dict:
    """Check CocoaPods installation."""
    success, stdout, stderr = run_command(['pod', '--version'])
    if success:
        return {
            'installed': True,
            'version': stdout.strip()
        }
    return {
        'installed': False,
        'hint': 'Install with: sudo gem install cocoapods'
    }


def check_homebrew() -> dict:
    """Check Homebrew installation."""
    success, stdout, stderr = run_command(['brew', '--version'])
    if success:
        version = stdout.split('\n')[0].strip()
        return {
            'installed': True,
            'version': version
        }
    return {
        'installed': False,
        'hint': 'Install from: https://brew.sh'
    }


def check_derived_data() -> dict:
    """Check DerivedData folder."""
    path = get_derived_data_path()
    if os.path.exists(path):
        # Calculate size
        total_size = 0
        item_count = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except (OSError, IOError):
                    pass
            item_count += len(dirnames) + len(filenames)

        return {
            'exists': True,
            'path': path,
            'size_bytes': total_size,
            'size_mb': round(total_size / (1024 * 1024), 1),
            'item_count': item_count
        }
    return {
        'exists': False,
        'path': path
    }


def main():
    parser = argparse.ArgumentParser(description='Diagnose Xcode environment')
    parser.add_argument('--verbose', action='store_true', help='Show detailed information')
    args = parser.parse_args()

    # Gather diagnostics
    diagnostics = {
        'system': {
            'os': 'macOS',
            'os_version': platform.mac_ver()[0],
            'architecture': platform.machine(),
            **get_macos_version()
        },
        'xcode_cli_tools': check_xcode_cli_tools(),
        'xcode': check_xcode(),
        'swift': check_swift(),
        'simulators': check_simulators(),
        'devices': check_devices(),
        'derived_data': check_derived_data(),
    }

    if args.verbose:
        diagnostics['platforms'] = get_available_platforms()
        diagnostics['cocoapods'] = check_cocoapods()
        diagnostics['homebrew'] = check_homebrew()

    # Determine overall status
    issues = []

    if not diagnostics['xcode_cli_tools'].get('installed'):
        issues.append('Xcode Command Line Tools not installed')

    if not diagnostics['xcode'].get('installed'):
        issues.append('Xcode not installed')

    if not diagnostics['swift'].get('installed'):
        issues.append('Swift not available')

    if diagnostics['simulators'].get('count', 0) == 0:
        issues.append('No simulators available')

    # Build response
    status = 'healthy' if not issues else 'issues_found'

    response = success_response(
        f'Environment check complete: {status}',
        status=status,
        issues=issues if issues else None,
        diagnostics=diagnostics
    )

    # Remove None values
    response = {k: v for k, v in response.items() if v is not None}

    print(json.dumps(response, indent=2))


if __name__ == '__main__':
    main()
