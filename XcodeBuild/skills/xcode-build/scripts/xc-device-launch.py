#!/usr/bin/env python3
"""
Launch an app on a connected physical device.

Usage:
    xc-device-launch.py --device <udid> --bundle-id <id>

Options:
    --device <udid>       Device UDID (from xc-devices.py)
    --bundle-id <id>      App bundle identifier

Output:
    JSON object with launch result
"""

import json
import sys
import argparse
import tempfile
import os

from xc_utils import run_xcrun, success_response, error_response


def main():
    parser = argparse.ArgumentParser(description='Launch app on device')
    parser.add_argument('--device', required=True, help='Device UDID')
    parser.add_argument('--bundle-id', required=True, help='App bundle identifier')
    args = parser.parse_args()

    # Create temp file for JSON output
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        json_path = f.name

    try:
        # Use devicectl to launch with terminate-existing
        success, stdout, stderr = run_xcrun(
            'devicectl', 'device', 'process', 'launch',
            '--device', args.device,
            '--terminate-existing',
            '--json-output', json_path,
            args.bundle_id
        )

        if success:
            # Try to get process ID from JSON output
            pid = None
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                        result = data.get('result', {})
                        pid = result.get('processID') or result.get('process', {}).get('processIdentifier')
                except (json.JSONDecodeError, KeyError):
                    pass

            response = success_response(
                'App launched successfully',
                device_udid=args.device,
                bundle_id=args.bundle_id,
                process_id=pid
            )

            response['next_steps'] = [
                f'Stop with: xc-device-stop.py --device {args.device} --bundle-id {args.bundle_id}'
            ]

            print(json.dumps(response, indent=2))
            return

        # Check for specific errors
        if 'unable to locate device' in stderr.lower():
            print(json.dumps(error_response(
                f'Device not found: {args.device}',
                hint='Use xc-devices.py to list connected devices'
            )))
            sys.exit(1)

        if 'app not installed' in stderr.lower() or 'no installed app' in stderr.lower():
            print(json.dumps(error_response(
                f'App not installed: {args.bundle_id}',
                hint='Use xc-device-install.py to install the app first'
            )))
            sys.exit(1)

        print(json.dumps(error_response(
            f'Failed to launch app: {stderr.strip()}',
            device_udid=args.device,
            bundle_id=args.bundle_id
        )))
        sys.exit(1)

    finally:
        if os.path.exists(json_path):
            os.unlink(json_path)


if __name__ == '__main__':
    main()
