#!/usr/bin/env python3
"""
Set the GPS location on an iOS Simulator.

Usage:
    sim-location.py --lat <latitude> --lon <longitude> [--udid <udid>]
    sim-location.py --clear [--udid <udid>]

Options:
    --lat <latitude>    Latitude (-90 to 90)
    --lon <longitude>   Longitude (-180 to 180)
    --clear             Clear simulated location
    --udid <udid>       Simulator UDID (uses booted if not specified)

Examples:
    sim-location.py --lat 37.7749 --lon -122.4194    # San Francisco
    sim-location.py --lat 40.7128 --lon -74.0060     # New York
    sim-location.py --lat 51.5074 --lon -0.1278      # London
    sim-location.py --lat 35.6762 --lon 139.6503     # Tokyo
    sim-location.py --clear                          # Reset to actual location

Output:
    JSON object with success status
"""

import json
import sys
import argparse

from sim_utils import run_simctl, get_booted_simulator_udid, handle_simctl_result


def set_location(udid, lat, lon):
    """Set location on the simulator."""
    success, stdout, stderr = run_simctl('location', udid, 'set', f'{lat},{lon}')
    return success, stderr


def clear_location(udid):
    """Clear simulated location."""
    success, stdout, stderr = run_simctl('location', udid, 'clear')
    return success, stderr


def main():
    parser = argparse.ArgumentParser(description='Set GPS location on iOS Simulator')
    parser.add_argument('--lat', type=float, help='Latitude')
    parser.add_argument('--lon', type=float, help='Longitude')
    parser.add_argument('--clear', action='store_true', help='Clear simulated location')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    args = parser.parse_args()

    # Validate args
    if not args.clear and (args.lat is None or args.lon is None):
        print(json.dumps({
            'success': False,
            'error': 'Either --lat and --lon, or --clear is required'
        }))
        sys.exit(1)

    # Validate coordinate ranges
    if args.lat is not None and (args.lat < -90 or args.lat > 90):
        print(json.dumps({
            'success': False,
            'error': 'Latitude must be between -90 and 90'
        }))
        sys.exit(1)

    if args.lon is not None and (args.lon < -180 or args.lon > 180):
        print(json.dumps({
            'success': False,
            'error': 'Longitude must be between -180 and 180'
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

    if args.clear:
        success, error = clear_location(udid)
        if not success:
            _, response = handle_simctl_result(
                success, error, operation='clear location',
                context={'udid': udid}
            )
            print(json.dumps(response))
            sys.exit(1)
        print(json.dumps({
            'success': True,
            'message': 'Location cleared',
            'udid': udid
        }))
        return

    # Set the location
    success, error = set_location(udid, args.lat, args.lon)

    if not success:
        _, response = handle_simctl_result(
            success, error, operation='set location',
            context={'udid': udid, 'latitude': args.lat, 'longitude': args.lon}
        )
        print(json.dumps(response))
        sys.exit(1)

    print(json.dumps({
        'success': True,
        'message': 'Location set',
        'latitude': args.lat,
        'longitude': args.lon,
        'udid': udid
    }))


if __name__ == '__main__':
    main()
