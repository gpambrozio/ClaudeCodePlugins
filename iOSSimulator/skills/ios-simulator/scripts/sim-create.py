#!/usr/bin/env python3
"""
Create a new iOS Simulator device.

Usage:
    sim-create.py --device "iPhone 15" [--runtime "iOS 18.0"] [--name "My Device"]
    sim-create.py --list-types
    sim-create.py --list-runtimes

Options:
    --device <type>         Device type to create (fuzzy match, e.g., "iPhone 15 Pro")
    --runtime <version>     iOS runtime (e.g., "iOS 18.0"). Defaults to latest.
    --name <name>           Custom device name. Defaults to the device type name.
    --list-types            List all available device types
    --list-runtimes         List all available iOS runtimes

Output:
    JSON object with success status and the UDID of the created device.

Notes:
    - Use --list-types and --list-runtimes to discover available options
    - Device type matching is fuzzy and case-insensitive
    - The created device starts in Shutdown state; use sim-boot.py to start it
"""

import json
import sys
import argparse

from sim_utils import run_simctl


def get_device_types():
    """Get available device types from simctl.

    Returns:
        List of dicts with 'name' and 'identifier' keys, or None on failure.
    """
    success, stdout, stderr = run_simctl('list', 'devicetypes', '-j')
    if not success:
        return None

    data = json.loads(stdout)
    return [
        {'name': dt.get('name', ''), 'identifier': dt.get('identifier', '')}
        for dt in data.get('devicetypes', [])
    ]


def get_runtimes():
    """Get available iOS runtimes from simctl.

    Returns:
        List of dicts with 'name', 'identifier', and 'isAvailable' keys, or None on failure.
    """
    success, stdout, stderr = run_simctl('list', 'runtimes', '-j')
    if not success:
        return None

    data = json.loads(stdout)
    runtimes = []
    for rt in data.get('runtimes', []):
        name = rt.get('name', '')
        identifier = rt.get('identifier', '')
        # Only include iOS runtimes
        if 'iOS' in name or 'iOS' in identifier:
            runtimes.append({
                'name': name,
                'identifier': identifier,
                'isAvailable': rt.get('isAvailable', False),
            })

    # Sort by identifier so latest is last
    runtimes.sort(key=lambda r: r['identifier'])
    return runtimes


def find_device_type(device_types, query):
    """Find a device type by fuzzy matching.

    Returns:
        Matching device type dict, or None.
    """
    query_lower = query.lower()

    # Exact match first
    for dt in device_types:
        if dt['name'].lower() == query_lower:
            return dt

    # Substring match
    for dt in device_types:
        if query_lower in dt['name'].lower():
            return dt

    return None


def find_runtime(runtimes, query):
    """Find a runtime by version string (e.g., '18.0', 'iOS 18.0').

    Returns:
        Matching runtime dict, or None.
    """
    query_lower = query.lower()
    for rt in runtimes:
        if query_lower in rt['name'].lower() or query_lower in rt['identifier'].lower():
            return rt
    return None


def main():
    parser = argparse.ArgumentParser(description='Create a new iOS Simulator device')
    parser.add_argument('--device', help='Device type (e.g., "iPhone 15 Pro")')
    parser.add_argument('--runtime', help='iOS runtime version (e.g., "iOS 18.0"). Defaults to latest.')
    parser.add_argument('--name', help='Custom device name')
    parser.add_argument('--list-types', action='store_true', help='List available device types')
    parser.add_argument('--list-runtimes', action='store_true', help='List available iOS runtimes')

    args = parser.parse_args()

    # List device types
    if args.list_types:
        types = get_device_types()
        if types is None:
            print(json.dumps({'success': False, 'error': 'Failed to get device types'}))
            sys.exit(1)
        print(json.dumps({
            'success': True,
            'count': len(types),
            'device_types': types
        }, indent=2))
        return

    # List runtimes
    if args.list_runtimes:
        runtimes = get_runtimes()
        if runtimes is None:
            print(json.dumps({'success': False, 'error': 'Failed to get runtimes'}))
            sys.exit(1)
        print(json.dumps({
            'success': True,
            'count': len(runtimes),
            'runtimes': runtimes
        }, indent=2))
        return

    # Create device
    if not args.device:
        print(json.dumps({
            'success': False,
            'error': 'Specify --device to create, or --list-types / --list-runtimes to discover options'
        }))
        sys.exit(1)

    # Resolve device type
    device_types = get_device_types()
    if not device_types:
        print(json.dumps({'success': False, 'error': 'Failed to get device types'}))
        sys.exit(1)

    matched_type = find_device_type(device_types, args.device)
    if not matched_type:
        print(json.dumps({
            'success': False,
            'error': f"Device type '{args.device}' not found. Use --list-types to see available options."
        }))
        sys.exit(1)

    # Resolve runtime
    runtimes = get_runtimes()
    if not runtimes:
        print(json.dumps({'success': False, 'error': 'No iOS runtimes available'}))
        sys.exit(1)

    if args.runtime:
        matched_runtime = find_runtime(runtimes, args.runtime)
        if not matched_runtime:
            print(json.dumps({
                'success': False,
                'error': f"Runtime '{args.runtime}' not found. Use --list-runtimes to see available options."
            }))
            sys.exit(1)
    else:
        # Use the latest available runtime
        available = [r for r in runtimes if r.get('isAvailable', False)]
        matched_runtime = available[-1] if available else runtimes[-1]

    # Build device name
    device_name = args.name or matched_type['name']

    # Create the simulator
    success, stdout, stderr = run_simctl(
        'create', device_name, matched_type['identifier'], matched_runtime['identifier']
    )

    if not success:
        print(json.dumps({
            'success': False,
            'error': f"Failed to create simulator: {stderr.strip()}"
        }))
        sys.exit(1)

    new_udid = stdout.strip()

    print(json.dumps({
        'success': True,
        'message': f"Created {device_name} ({matched_runtime['name']})",
        'udid': new_udid,
        'name': device_name,
        'device_type': matched_type['name'],
        'device_type_id': matched_type['identifier'],
        'runtime': matched_runtime['name'],
        'runtime_id': matched_runtime['identifier'],
    }, indent=2))


if __name__ == '__main__':
    main()
