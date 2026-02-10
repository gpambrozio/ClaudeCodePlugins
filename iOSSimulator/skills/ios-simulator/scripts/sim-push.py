#!/usr/bin/env python3
"""
Send simulated push notifications to an iOS Simulator app.

Supports simple notifications (title/body/badge) and custom JSON payloads.

Usage:
    sim-push.py --bundle-id <id> --title "Alert" --body "Message"
    sim-push.py --bundle-id <id> --payload '{"aps":{"alert":"Hello"}}'
    sim-push.py --bundle-id <id> --payload-file notification.json

Options:
    --bundle-id, -b <id>    App bundle identifier (required)
    --title <text>          Alert title
    --body <text>           Alert body message
    --badge <number>        Badge number to display
    --no-sound              Don't include sound in notification
    --payload <json>        Custom JSON payload (inline string)
    --payload-file <path>   Custom JSON payload from file
    --udid <udid>           Simulator UDID (uses booted if not specified)

Output:
    JSON object with success status and the payload that was sent.

Notes:
    - The app must be installed on the simulator
    - Payloads are automatically wrapped in an "aps" dictionary if missing
    - Use --payload or --payload-file for complex notification payloads
"""

import json
import sys
import os
import argparse
import tempfile

from sim_utils import get_booted_simulator_udid, run_simctl


def build_simple_payload(title=None, body=None, badge=None, sound=True):
    """Build an APNs payload from simple parameters."""
    alert = {}
    if title:
        alert['title'] = title
    if body:
        alert['body'] = body

    aps = {}
    if alert:
        aps['alert'] = alert
    if badge is not None:
        aps['badge'] = badge
    if sound:
        aps['sound'] = 'default'

    return {'aps': aps}


def send_push(udid, bundle_id, payload):
    """Send a push notification using a payload dict.

    Returns:
        Tuple of (success, error_message)
    """
    # Ensure payload has aps wrapper
    if 'aps' not in payload:
        payload = {'aps': payload}

    # Write to temp file (simctl push requires a file)
    fd, temp_path = tempfile.mkstemp(suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f)

        success, stdout, stderr = run_simctl('push', udid, bundle_id, temp_path)
        if not success:
            return False, stderr.strip()
        return True, None
    finally:
        os.unlink(temp_path)


def main():
    parser = argparse.ArgumentParser(description='Send push notification to iOS Simulator app')
    parser.add_argument('--bundle-id', '-b', required=True, help='App bundle identifier')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')

    # Simple payload options
    simple_group = parser.add_argument_group('simple notification')
    simple_group.add_argument('--title', help='Alert title')
    simple_group.add_argument('--body', help='Alert body message')
    simple_group.add_argument('--badge', type=int, help='Badge number')
    simple_group.add_argument('--no-sound', action='store_true',
                              help="Don't include sound")

    # Custom payload options
    custom_group = parser.add_argument_group('custom payload')
    custom_group.add_argument('--payload', help='Inline JSON payload string')
    custom_group.add_argument('--payload-file', help='Path to JSON payload file')

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

    # Build or parse payload
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
            print(json.dumps({
                'success': False,
                'error': f'Invalid JSON payload: {e}'
            }))
            sys.exit(1)
    elif args.payload_file:
        if not os.path.exists(args.payload_file):
            print(json.dumps({
                'success': False,
                'error': f'Payload file not found: {args.payload_file}'
            }))
            sys.exit(1)
        with open(args.payload_file) as f:
            try:
                payload = json.load(f)
            except json.JSONDecodeError as e:
                print(json.dumps({
                    'success': False,
                    'error': f'Invalid JSON in payload file: {e}'
                }))
                sys.exit(1)
    elif args.title or args.body or args.badge is not None:
        payload = build_simple_payload(
            title=args.title,
            body=args.body,
            badge=args.badge,
            sound=not args.no_sound
        )
    else:
        print(json.dumps({
            'success': False,
            'error': 'Provide --title/--body/--badge for simple notification, '
                     'or --payload/--payload-file for custom payload'
        }))
        sys.exit(1)

    # Send it
    success, error = send_push(udid, args.bundle_id, payload)

    if success:
        print(json.dumps({
            'success': True,
            'message': f'Push notification sent to {args.bundle_id}',
            'bundle_id': args.bundle_id,
            'udid': udid,
            'payload': payload
        }, indent=2))
    else:
        print(json.dumps({
            'success': False,
            'error': f'Failed to send push notification: {error}',
            'bundle_id': args.bundle_id,
            'udid': udid
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
