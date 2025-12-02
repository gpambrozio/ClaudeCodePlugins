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

from sim_utils import run_simctl, get_booted_simulator_udid


def take_screenshot(udid, output_path, mask='ignored'):
    """Take a screenshot of the simulator."""
    args = ['io', udid, 'screenshot']
    if mask != 'ignored':
        args.extend(['--mask', mask])
    args.append(output_path)

    success, stdout, stderr = run_simctl(*args)
    return success, stderr


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
        print(json.dumps({
            'success': False,
            'error': error.strip() if error else 'Failed to take screenshot'
        }))
        sys.exit(1)

    # Verify file exists
    if not os.path.exists(output_path):
        print(json.dumps({
            'success': False,
            'error': 'Screenshot file was not created'
        }))
        sys.exit(1)

    file_size = os.path.getsize(output_path)

    print(json.dumps({
        'success': True,
        'message': 'Screenshot saved',
        'path': output_path,
        'udid': udid,
        'size_bytes': file_size
    }))


if __name__ == '__main__':
    main()
