#!/usr/bin/env python3
"""
Open a URL on an iOS Simulator.

Usage:
    sim-openurl.py --url <url> [--udid <udid>]
    sim-openurl.py <url>

Options:
    --url <url>    URL to open (http://, https://, or custom scheme)
    --udid <udid>  Simulator UDID (uses booted if not specified)

Examples:
    sim-openurl.py --url "https://apple.com"
    sim-openurl.py --url "maps://?q=coffee"
    sim-openurl.py --url "myapp://deeplink/path"

Output:
    JSON object with success status
"""

import subprocess
import json
import sys
import argparse


def run_simctl(*args):
    """Run xcrun simctl command and return output."""
    cmd = ['xcrun', 'simctl'] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def get_booted_simulator():
    """Get the first booted simulator's UDID."""
    cmd = ['xcrun', 'simctl', 'list', '-j', 'devices']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    data = json.loads(result.stdout)
    for runtime, devices in data.get('devices', {}).items():
        for device in devices:
            if device.get('state') == 'Booted':
                return device.get('udid')
    return None


def open_url(udid, url):
    """Open a URL on the simulator."""
    success, stdout, stderr = run_simctl('openurl', udid, url)
    return success, stderr


def main():
    parser = argparse.ArgumentParser(description='Open URL on iOS Simulator')
    parser.add_argument('--url', '-u', help='URL to open')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('url_positional', nargs='?', help='URL to open (positional)')
    args = parser.parse_args()

    # Get URL from either flag or positional
    url = args.url or args.url_positional
    if not url:
        print(json.dumps({
            'success': False,
            'error': 'URL is required. Use --url or provide as argument.'
        }))
        sys.exit(1)

    # Get UDID
    udid = args.udid
    if not udid:
        udid = get_booted_simulator()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    # Open the URL
    success, error = open_url(udid, url)

    if not success:
        print(json.dumps({
            'success': False,
            'error': error.strip() if error else 'Failed to open URL'
        }))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': 'URL opened',
        'url': url,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
