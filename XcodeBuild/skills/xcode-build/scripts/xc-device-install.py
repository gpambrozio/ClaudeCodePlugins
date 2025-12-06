#!/usr/bin/env python3
"""
Install an app on a connected physical device.

Usage:
    xc-device-install.py --device <udid> --app <path>

Options:
    --device <udid>    Device UDID (from xc-devices.py)
    --app <path>       Path to .app bundle

Output:
    JSON object with installation result
"""

import json
import sys
import argparse
import os
import tempfile
import plistlib

from xc_utils import run_xcrun, success_response, error_response


def get_bundle_id(app_path: str) -> str:
    """Extract bundle ID from app's Info.plist."""
    info_plist = os.path.join(app_path, 'Info.plist')
    if not os.path.exists(info_plist):
        return None

    try:
        with open(info_plist, 'rb') as f:
            plist = plistlib.load(f)
            return plist.get('CFBundleIdentifier')
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='Install app on device')
    parser.add_argument('--device', required=True, help='Device UDID')
    parser.add_argument('--app', required=True, help='Path to .app bundle')
    args = parser.parse_args()

    app_path = os.path.abspath(args.app)

    if not os.path.exists(app_path):
        print(json.dumps(error_response(f'App not found: {app_path}')))
        sys.exit(1)

    if not app_path.endswith('.app'):
        print(json.dumps(error_response('Path must be a .app bundle')))
        sys.exit(1)

    # Get bundle ID for reference
    bundle_id = get_bundle_id(app_path)

    # Try devicectl first (Xcode 15+)
    success, stdout, stderr = run_xcrun(
        'devicectl', 'device', 'install', 'app',
        '--device', args.device,
        app_path
    )

    if success:
        response = success_response(
            'App installed successfully',
            device_udid=args.device,
            app_path=app_path,
            bundle_id=bundle_id
        )
        if bundle_id:
            response['next_steps'] = [
                f'Launch with: xc-device-launch.py --device {args.device} --bundle-id {bundle_id}'
            ]
        print(json.dumps(response, indent=2))
        return

    # Check for specific errors
    if 'unable to locate device' in stderr.lower() or 'device not found' in stderr.lower():
        print(json.dumps(error_response(
            f'Device not found: {args.device}',
            hint='Use xc-devices.py to list connected devices'
        )))
        sys.exit(1)

    if 'signing' in stderr.lower() or 'codesign' in stderr.lower():
        print(json.dumps(error_response(
            'Code signing error',
            details=stderr.strip(),
            hint='Ensure the app is signed for development and device is registered'
        )))
        sys.exit(1)

    print(json.dumps(error_response(
        f'Failed to install app: {stderr.strip()}',
        device_udid=args.device,
        app_path=app_path
    )))
    sys.exit(1)


if __name__ == '__main__':
    main()
