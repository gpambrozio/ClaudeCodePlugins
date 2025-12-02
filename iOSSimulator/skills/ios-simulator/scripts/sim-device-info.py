#!/usr/bin/env python3
"""
Get detailed information about an iOS Simulator device.

Usage:
    sim-device-info.py [--udid <udid>]

Options:
    --udid <udid>  Simulator UDID (uses booted if not specified)

Output:
    JSON object with device details including screen dimensions and scale factor

Example Output:
    {
        "success": true,
        "name": "iPhone 17 Pro",
        "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "state": "Booted",
        "runtime": "iOS-26-1",
        "device_type": "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro",
        "model_identifier": "iPhone18,1",
        "screen": {
            "scale": 3,
            "width_pixels": 1206,
            "height_pixels": 2622,
            "width_points": 402,
            "height_points": 874,
            "ppi": 460
        }
    }
"""

import json
import sys
import argparse
import os
import plistlib

from sim_utils import run_simctl, get_booted_simulator_udid


def get_device_info(udid):
    """Get device info from simctl."""
    success, stdout, stderr = run_simctl('list', '-j', 'devices')
    if not success:
        return None, stderr

    data = json.loads(stdout)
    for runtime, devices in data.get('devices', {}).items():
        for device in devices:
            if device.get('udid') == udid:
                device['runtime'] = runtime.split('.')[-1]
                return device, None

    return None, f"Device with UDID {udid} not found"


def get_device_profile(device_type_identifier):
    """
    Read the device profile from the device type bundle.

    The profile.plist contains screen dimensions and scale factor.
    """
    base_path = "/Library/Developer/CoreSimulator/Profiles/DeviceTypes"

    if not os.path.exists(base_path):
        return None, "CoreSimulator DeviceTypes not found"

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
                return profile, None
        except Exception as e:
            continue

    return None, f"Device profile not found for {device_type_identifier}"


def main():
    parser = argparse.ArgumentParser(description='Get iOS Simulator device info')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
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

    # Get device info
    device_info, error = get_device_info(udid)
    if not device_info:
        print(json.dumps({
            'success': False,
            'error': error or 'Failed to get device info'
        }))
        sys.exit(1)

    device_type = device_info.get('deviceTypeIdentifier', '')

    # Get device profile for screen info
    profile, profile_error = get_device_profile(device_type)

    result = {
        'success': True,
        'name': device_info.get('name'),
        'udid': udid,
        'state': device_info.get('state'),
        'runtime': device_info.get('runtime'),
        'device_type': device_type,
    }

    if profile:
        scale = profile.get('mainScreenScale', 1)
        width_pixels = profile.get('mainScreenWidth', 0)
        height_pixels = profile.get('mainScreenHeight', 0)

        # Calculate points (divide pixels by scale)
        width_points = int(width_pixels / scale) if scale else width_pixels
        height_points = int(height_pixels / scale) if scale else height_pixels

        result['model_identifier'] = profile.get('modelIdentifier')
        result['screen'] = {
            'scale': int(scale),
            'width_pixels': width_pixels,
            'height_pixels': height_pixels,
            'width_points': width_points,
            'height_points': height_points,
            'ppi': profile.get('mainScreenWidthDPI', profile.get('mainScreenHeightDPI'))
        }
    else:
        result['screen'] = None
        result['screen_error'] = profile_error

    print(json.dumps(result))


if __name__ == '__main__':
    main()
