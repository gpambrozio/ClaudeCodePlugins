#!/usr/bin/env python3
"""
Stop a running app on a connected physical device.

Usage:
    xc-device-stop.py --device <udid> --bundle-id <id>

Options:
    --device <udid>       Device UDID (from xc-devices.py)
    --bundle-id <id>      App bundle identifier

Output:
    JSON object with stop result
"""

import json
import sys
import argparse

from xc_utils import run_xcrun, success_response, error_response


def main():
    parser = argparse.ArgumentParser(description='Stop app on device')
    parser.add_argument('--device', required=True, help='Device UDID')
    parser.add_argument('--bundle-id', required=True, help='App bundle identifier')
    args = parser.parse_args()

    # Use devicectl to terminate
    success, stdout, stderr = run_xcrun(
        'devicectl', 'device', 'process', 'terminate',
        '--device', args.device,
        args.bundle_id
    )

    if success:
        print(json.dumps(success_response(
            'App stopped successfully',
            device_udid=args.device,
            bundle_id=args.bundle_id
        ), indent=2))
        return

    # Check if app was not running (treat as success)
    if 'not running' in stderr.lower() or 'no such process' in stderr.lower():
        print(json.dumps(success_response(
            'App was not running',
            device_udid=args.device,
            bundle_id=args.bundle_id
        ), indent=2))
        return

    # Check for device errors
    if 'unable to locate device' in stderr.lower():
        print(json.dumps(error_response(
            f'Device not found: {args.device}',
            hint='Use xc-devices.py to list connected devices'
        )))
        sys.exit(1)

    print(json.dumps(error_response(
        f'Failed to stop app: {stderr.strip()}',
        device_udid=args.device,
        bundle_id=args.bundle_id
    )))
    sys.exit(1)


if __name__ == '__main__':
    main()
