#!/usr/bin/env python3
"""
Take a screenshot of an iOS Simulator.

Usage:
    sim-screenshot.py --udid <udid> [--output <path>]
    sim-screenshot.py [--output <path>]  # Uses booted simulator

Options:
    --udid <udid>      Simulator UDID (optional, uses booted if not specified)
    --output <path>    Output file path (default: /tmp/sim-screenshot-<timestamp>.png)
    --mask <type>      Mask type: ignored, alpha, black (default: ignored)

Output:
    JSON object with success status and file path
"""

import json
import sys
import argparse
import time
import os
import plistlib

from sim_utils import run_simctl, get_booted_simulator_udid, handle_simctl_result


def take_screenshot(udid, output_path, mask='ignored'):
    """Take a screenshot of the simulator."""
    args = ['io', udid, 'screenshot']
    if mask != 'ignored':
        args.extend(['--mask', mask])
    args.append(output_path)

    success, stdout, stderr = run_simctl(*args)
    return success, stderr


def get_device_type(udid):
    """Get device type identifier for a simulator."""
    success, stdout, stderr = run_simctl('list', '-j', 'devices')
    if not success:
        return None

    data = json.loads(stdout)
    for runtime, devices in data.get('devices', {}).items():
        for device in devices:
            if device.get('udid') == udid:
                return device.get('deviceTypeIdentifier')
    return None


def get_screen_info(device_type_identifier):
    """
    Get screen info from the device type profile.

    Returns dict with scale, width_pixels, height_pixels, width_points, height_points
    or None if not found.
    """
    base_path = "/Library/Developer/CoreSimulator/Profiles/DeviceTypes"

    if not os.path.exists(base_path):
        return None

    for entry in os.listdir(base_path):
        if not entry.endswith('.simdevicetype'):
            continue

        bundle_path = os.path.join(base_path, entry)
        info_path = os.path.join(bundle_path, "Contents/Info.plist")
        profile_path = os.path.join(bundle_path, "Contents/Resources/profile.plist")

        if not os.path.exists(info_path) or not os.path.exists(profile_path):
            continue

        try:
            with open(info_path, 'rb') as f:
                info = plistlib.load(f)

            if info.get('CFBundleIdentifier') == device_type_identifier:
                with open(profile_path, 'rb') as f:
                    profile = plistlib.load(f)

                scale = profile.get('mainScreenScale', 1)
                width_pixels = profile.get('mainScreenWidth', 0)
                height_pixels = profile.get('mainScreenHeight', 0)

                return {
                    'scale': int(scale),
                    'width_pixels': width_pixels,
                    'height_pixels': height_pixels,
                    'width_points': int(width_pixels / scale) if scale else width_pixels,
                    'height_points': int(height_pixels / scale) if scale else height_pixels,
                }
        except Exception:
            continue

    return None


def main():
    parser = argparse.ArgumentParser(description='Take iOS Simulator screenshot')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--mask', choices=['ignored', 'alpha', 'black'],
                        default='ignored', help='Screenshot mask type')
    args = parser.parse_args()

    # Get UDID
    udid = args.udid
    if not udid:
        udid = get_booted_simulator_udid()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    # Generate output path if not specified
    output_path = args.output
    if not output_path:
        timestamp = int(time.time() * 1000)
        output_path = f'/tmp/sim-screenshot-{timestamp}.png'

    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Take screenshot
    success, error = take_screenshot(udid, output_path, args.mask)

    if not success:
        _, response = handle_simctl_result(
            success, error, operation='take screenshot',
            context={'output_path': output_path, 'udid': udid}
        )
        print(json.dumps(response))
        sys.exit(1)

    # Verify file exists
    if not os.path.exists(output_path):
        print(json.dumps({
            'success': False,
            'error': 'Screenshot file was not created'
        }))
        sys.exit(1)

    file_size = os.path.getsize(output_path)

    result = {
        'success': True,
        'message': 'Screenshot saved',
        'path': output_path,
        'udid': udid,
        'size_bytes': file_size
    }

    # Add screen info for coordinate conversion
    device_type = get_device_type(udid)
    if device_type:
        screen_info = get_screen_info(device_type)
        if screen_info:
            result['screen'] = screen_info

    print(json.dumps(result))


if __name__ == '__main__':
    main()
