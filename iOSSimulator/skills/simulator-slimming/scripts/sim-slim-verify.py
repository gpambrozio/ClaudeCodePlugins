#!/usr/bin/env python3
"""
Check that a simulator is still in exactly the slim state you configured.

The disable overrides are per-simulator state that is easy to lose without
noticing: erase, delete-and-recreate, "Erase All Content and Settings", or a
simulator from a newly installed runtime all come up stock, and nothing fails
loudly when that happens - the simulator just quietly runs heavy again.

Where sim-slim-doctor.py answers "do the features my tests need still work?",
this answers "is this simulator in exactly the state I configured?". Re-running
sim-slim.py is idempotent, so the repair is a one-liner:

    sim-slim-verify.py --profile ci.json || sim-slim.py --profile ci.json

Usage:
    sim-slim-verify.py [--profile ci.json] [--except <ids>] [--keep <labels>]

Options:
    --udid <udid>     Simulator to verify (defaults to the booted one)
    --name <name>     Simulator to verify, by name
    --except <ids>    Same selection you passed to sim-slim.py
    --keep <labels>   Same selection you passed to sim-slim.py
    --profile <path>  Same profile file you passed to sim-slim.py

Exit code:
    0 when the state matches, 1 on drift or error.

Output:
    JSON object on stdout.
"""

import argparse
import json
import sys

import slim_catalog as catalog
import slim_launchd as launchd


def main():
    parser = argparse.ArgumentParser(description='Verify a simulator matches a slimming profile')
    parser.add_argument('--udid', help='Simulator UDID (defaults to the booted one)')
    parser.add_argument('--name', help='Simulator name')
    parser.add_argument('--except', dest='except_ids', default='',
                        help='Comma-separated category IDs left fully enabled')
    parser.add_argument('--keep', default='',
                        help='Comma-separated launchd labels left enabled')
    parser.add_argument('--profile', help='Path to the JSON profile file')
    args = parser.parse_args()

    try:
        device = launchd.resolve_device(args.udid, args.name)
    except launchd.SlimError as exc:
        launchd.fail(str(exc))
        return

    # The device under verification decides which catalog its state is held
    # against; see the same ordering in sim-slim.py.
    try:
        catalog.select_platform(device['platform'])
        profile = catalog.build_profile(
            catalog.parse_list(args.except_ids), catalog.parse_list(args.keep), args.profile)
    except catalog.ProfileError as exc:
        launchd.fail(str(exc), **launchd.device_summary(device))
        return

    managed = catalog.managed_labels()

    try:
        if device['state'] != 'Booted':
            launchd.fail('simulator must be booted to read its state (it is {})'.format(
                device['state']), **launchd.device_summary(device))
            return
        disabled = launchd.read_disabled(device)
    except launchd.SlimError as exc:
        launchd.fail(str(exc))
        return

    # Unmanaged labels are never this tool's business, so a daemon disabled by
    # something else does not count as drift.
    missing = sorted(label for label in profile['desired'] if label not in disabled)
    extra = sorted(label for label in disabled if label in managed
                   and label not in profile['desired'])
    ok = not missing and not extra

    result = {
        'success': True,
        'ok': ok,
        'profile': {'except': profile['except'], 'keep': profile['keep']},
        'missing': missing,
        'extra': extra,
        'disabled_total': len(disabled & managed),
        'expected_total': len(profile['desired']),
    }
    if not ok:
        command = 'sim-slim.py'
        if args.profile:
            command += ' --profile {}'.format(args.profile)
        else:
            if profile['except']:
                command += ' --except {}'.format(','.join(profile['except']))
            if profile['keep']:
                command += ' --keep {}'.format(','.join(profile['keep']))
        result['remedy'] = 're-run `{}` to repair the drift (it is idempotent)'.format(command)
    result.update(launchd.device_summary(device))
    print(json.dumps(result))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
