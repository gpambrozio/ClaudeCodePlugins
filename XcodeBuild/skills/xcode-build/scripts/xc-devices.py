#!/usr/bin/env python3
"""
List connected Apple devices (iPhone, iPad, Apple Watch, etc.).

Usage:
    xc-devices.py [--available] [--json-raw]

Options:
    --available    Show only available (paired) devices
    --json-raw     Output raw devicectl JSON

Output:
    JSON object with list of connected devices
"""

import json
import sys
import argparse
import tempfile
import os

from xc_utils import run_xcrun, run_command, success_response, error_response


def parse_device_info(device: dict) -> dict:
    """Extract relevant device information from devicectl output."""
    hardware = device.get('hardwareProperties', {})
    device_props = device.get('deviceProperties', {})
    connection = device.get('connectionProperties', {})

    # Determine platform
    platform_id = hardware.get('platform', '').lower()
    platform_map = {
        'iphoneos': 'iOS',
        'ipados': 'iPadOS',
        'watchos': 'watchOS',
        'tvos': 'tvOS',
        'xros': 'visionOS',
    }
    platform = platform_map.get(platform_id, platform_id.upper() if platform_id else 'Unknown')

    # Determine connection type
    transport = connection.get('transportType', '').lower()
    is_wifi = 'wifi' in transport or 'network' in transport

    # Check pairing/availability
    is_paired = device_props.get('developerModeStatus', '') == 'enabled' or \
                connection.get('pairingState', '') == 'paired'

    return {
        'name': device_props.get('name', 'Unknown'),
        'udid': device.get('identifier', ''),
        'platform': platform,
        'os_version': device_props.get('osVersionNumber', ''),
        'model': hardware.get('marketingName', hardware.get('deviceType', 'Unknown')),
        'model_id': hardware.get('productType', ''),
        'architecture': hardware.get('cpuType', {}).get('name', ''),
        'connection': 'WiFi' if is_wifi else 'USB',
        'is_paired': is_paired,
        'available': is_paired,
    }


def list_devices_devicectl() -> tuple:
    """List devices using xcrun devicectl (modern method, Xcode 15+)."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        json_path = f.name

    try:
        success, stdout, stderr = run_xcrun(
            'devicectl', 'list', 'devices', '--json-output', json_path
        )

        if not success:
            return None, f'devicectl failed: {stderr}'

        if not os.path.exists(json_path):
            return None, 'devicectl did not produce output'

        with open(json_path, 'r') as f:
            data = json.load(f)

        return data, None
    except json.JSONDecodeError as e:
        return None, f'Failed to parse devicectl output: {e}'
    finally:
        if os.path.exists(json_path):
            os.unlink(json_path)


def list_devices_xctrace() -> tuple:
    """List devices using xcrun xctrace (fallback method)."""
    success, stdout, stderr = run_xcrun('xctrace', 'list', 'devices')

    if not success:
        return None, f'xctrace failed: {stderr}'

    devices = []
    lines = stdout.strip().split('\n')

    for line in lines:
        line = line.strip()
        # Skip headers and simulators
        if not line or line.startswith('==') or 'Simulator' in line:
            continue

        # Parse device line: "Name (OS Version) (UDID)"
        # Example: "iPhone 15 Pro (17.0) (00008120-000000000000000E)"
        import re
        match = re.match(r'^(.+?)\s+\(([^)]+)\)\s+\(([A-F0-9-]+)\)$', line)
        if match:
            devices.append({
                'name': match.group(1).strip(),
                'os_version': match.group(2),
                'udid': match.group(3),
                'platform': 'iOS',  # xctrace doesn't distinguish
                'connection': 'Unknown',
                'available': True,
            })

    return {'devices': devices}, None


def main():
    parser = argparse.ArgumentParser(description='List connected Apple devices')
    parser.add_argument('--available', action='store_true', help='Show only available devices')
    parser.add_argument('--json-raw', action='store_true', help='Output raw JSON from devicectl')
    args = parser.parse_args()

    # Try modern devicectl first
    data, error = list_devices_devicectl()

    # Fall back to xctrace if devicectl fails
    if data is None:
        data, error = list_devices_xctrace()

        if data is None:
            print(json.dumps(error_response(
                f'Failed to list devices: {error}',
                hint='Ensure Xcode is installed and a device is connected'
            )))
            sys.exit(1)

        # xctrace returns simpler format
        devices = data.get('devices', [])
        if args.available:
            devices = [d for d in devices if d.get('available', True)]

        print(json.dumps(success_response(
            f'Found {len(devices)} device(s) (via xctrace)',
            method='xctrace',
            devices=devices,
            count=len(devices)
        ), indent=2))
        return

    if args.json_raw:
        print(json.dumps(data, indent=2))
        return

    # Parse devicectl output
    result = data.get('result', {})
    raw_devices = result.get('devices', [])

    devices = []
    for raw_device in raw_devices:
        # Skip simulators
        hardware = raw_device.get('hardwareProperties', {})
        if hardware.get('deviceType', '').lower() == 'simulator':
            continue

        device = parse_device_info(raw_device)
        devices.append(device)

    if args.available:
        devices = [d for d in devices if d.get('available', False)]

    # Group by connection type
    usb_devices = [d for d in devices if d.get('connection') == 'USB']
    wifi_devices = [d for d in devices if d.get('connection') == 'WiFi']

    response = success_response(
        f'Found {len(devices)} device(s)',
        method='devicectl',
        devices=devices,
        count=len(devices),
        by_connection={
            'usb': len(usb_devices),
            'wifi': len(wifi_devices)
        }
    )

    if not devices:
        response['hint'] = 'Connect a device via USB or enable WiFi debugging'

    print(json.dumps(response, indent=2))


if __name__ == '__main__':
    main()
