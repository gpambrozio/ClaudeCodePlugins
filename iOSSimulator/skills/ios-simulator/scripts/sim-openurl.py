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

import json
import sys
import argparse

from sim_utils import run_simctl, get_booted_simulator_udid, handle_simctl_result


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
        udid = get_booted_simulator_udid()
        if not udid:
            print(json.dumps({
                'success': False,
                'error': 'No booted simulator found. Boot a simulator first or specify --udid'
            }))
            sys.exit(1)

    # Open the URL
    success, error = open_url(udid, url)

    if not success:
        _, response = handle_simctl_result(
            success, error, operation='open URL',
            context={'url': url, 'udid': udid}
        )
        print(json.dumps(response))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': 'URL opened',
        'url': url,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
