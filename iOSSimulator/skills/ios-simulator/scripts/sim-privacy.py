#!/usr/bin/env python3
"""
Manage app privacy permissions on an iOS Simulator.

Grant, revoke, or reset app permissions for testing permission flows.

Usage:
    sim-privacy.py --grant <service> --bundle-id <id>
    sim-privacy.py --revoke <service> --bundle-id <id>
    sim-privacy.py --reset <service> --bundle-id <id>
    sim-privacy.py --reset-all --bundle-id <id>
    sim-privacy.py --list

Options:
    --grant <service>       Grant permission (single service or comma-separated)
    --revoke <service>      Revoke permission
    --reset <service>       Reset permission to default (triggers prompt again)
    --reset-all             Reset all permissions for the app
    --list                  List all supported services
    --bundle-id, -b <id>    App bundle identifier (required for grant/revoke/reset)
    --udid <udid>           Simulator UDID (uses booted if not specified)

Supported services:
    camera, microphone, location, contacts, photos, calendar,
    health, reminders, motion, keyboard, mediaLibrary, calls, siri

Output:
    JSON object with success status and details of what was changed.
"""

import json
import sys
import argparse

from sim_utils import get_booted_simulator_udid, run_simctl

SUPPORTED_SERVICES = {
    'camera': 'Camera access',
    'microphone': 'Microphone access',
    'location': 'Location services',
    'contacts': 'Contacts access',
    'photos': 'Photos library access',
    'calendar': 'Calendar access',
    'health': 'Health data access',
    'reminders': 'Reminders access',
    'motion': 'Motion & fitness',
    'keyboard': 'Keyboard access',
    'mediaLibrary': 'Media library',
    'calls': 'Call history',
    'siri': 'Siri access',
}


def privacy_action(udid, action, service, bundle_id):
    """Execute a privacy action (grant/revoke/reset) for a single service.

    Returns:
        Tuple of (success, error_message)
    """
    success, stdout, stderr = run_simctl('privacy', udid, action, service, bundle_id)
    if not success:
        return False, stderr.strip()
    return True, None


def main():
    parser = argparse.ArgumentParser(description='Manage iOS app privacy permissions')
    parser.add_argument('--bundle-id', '-b', help='App bundle identifier')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--grant', help='Grant permission (service or comma-separated list)')
    action_group.add_argument('--revoke', help='Revoke permission (service or comma-separated list)')
    action_group.add_argument('--reset', help='Reset permission (service or comma-separated list)')
    action_group.add_argument('--reset-all', action='store_true',
                              help='Reset all permissions for the app')
    action_group.add_argument('--list', action='store_true', help='List supported services')

    args = parser.parse_args()

    # List mode
    if args.list:
        print(json.dumps({
            'success': True,
            'services': {name: desc for name, desc in SUPPORTED_SERVICES.items()}
        }, indent=2))
        return

    # All other actions require --bundle-id
    if not args.bundle_id:
        print(json.dumps({
            'success': False,
            'error': '--bundle-id is required for grant/revoke/reset operations'
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

    # Reset all permissions
    if args.reset_all:
        success, stdout, stderr = run_simctl('privacy', udid, 'reset', 'all', args.bundle_id)
        if success:
            print(json.dumps({
                'success': True,
                'message': f'Reset all permissions for {args.bundle_id}',
                'action': 'reset',
                'services': 'all',
                'bundle_id': args.bundle_id,
                'udid': udid
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Failed to reset permissions: {stderr.strip()}',
                'bundle_id': args.bundle_id,
                'udid': udid
            }))
            sys.exit(1)
        return

    # Determine action and services
    if args.grant:
        action = 'grant'
        services_str = args.grant
    elif args.revoke:
        action = 'revoke'
        services_str = args.revoke
    else:
        action = 'reset'
        services_str = args.reset

    services = [s.strip() for s in services_str.split(',')]

    # Validate services
    invalid = [s for s in services if s not in SUPPORTED_SERVICES]
    if invalid:
        print(json.dumps({
            'success': False,
            'error': f"Unknown service(s): {', '.join(invalid)}",
            'supported_services': list(SUPPORTED_SERVICES.keys())
        }))
        sys.exit(1)

    # Execute action for each service
    results = []
    all_success = True
    for service in services:
        success, error = privacy_action(udid, action, service, args.bundle_id)
        results.append({
            'service': service,
            'description': SUPPORTED_SERVICES[service],
            'success': success,
        })
        if not success:
            results[-1]['error'] = error
            all_success = False

    response = {
        'success': all_success,
        'action': action,
        'bundle_id': args.bundle_id,
        'udid': udid,
        'results': results,
    }
    if all_success:
        svc_list = ', '.join(services)
        response['message'] = f"{action.capitalize()} {svc_list} for {args.bundle_id}"

    print(json.dumps(response, indent=2))

    if not all_success:
        sys.exit(1)


if __name__ == '__main__':
    main()
