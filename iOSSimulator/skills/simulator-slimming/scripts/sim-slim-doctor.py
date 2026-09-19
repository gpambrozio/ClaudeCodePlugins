#!/usr/bin/env python3
"""
Check that the capabilities a test suite needs still work on a slimmed simulator.

Slimming turns features off on purpose, and a test that needs one of them fails
in ways that look like an app bug - a push that never arrives, a purchase sheet
that never appears. Naming the required features up front turns that into a
fast, explicit preflight: this exits non-zero when any of them is broken, so a
CI step can stop before running the suite.

Feature IDs are finer-grained than slimming categories: each maps to just the
daemons that back one capability.

Usage:
    sim-slim-doctor.py --requires push,storekit,universal-links
    sim-slim-doctor.py --list

Options:
    --requires <ids>  Comma-separated feature IDs the simulator must support
    --list            List every known feature and the daemons it needs
    --udid <udid>     Simulator to check (defaults to the booted one)
    --name <name>     Simulator to check, by name

Exit code:
    0 when every required feature is OK, 1 when any is broken or on error.

Output:
    JSON object on stdout.
"""

import argparse
import json
import sys

import slim_catalog as catalog
import slim_launchd as launchd


def main():
    parser = argparse.ArgumentParser(description='Check required features on a slimmed simulator')
    parser.add_argument('--requires', default='',
                        help='Comma-separated feature IDs that must work')
    parser.add_argument('--list', action='store_true', help='List every known feature')
    parser.add_argument('--udid', help='Simulator UDID (defaults to the booted one)')
    parser.add_argument('--name', help='Simulator name')
    args = parser.parse_args()

    if args.list:
        features = [{
            'id': feature['id'],
            'name': feature['name'],
            'labels': [{'label': label, 'purpose': catalog.describe_service(label)}
                       for label in feature['labels']],
        } for feature in catalog.features()]
        print(json.dumps({'success': True, 'features': features}))
        return

    required = catalog.parse_list(args.requires)
    if not required:
        launchd.fail('--requires is empty; name the features to check, or pass --list')
        return

    try:
        device = launchd.resolve_device(args.udid, args.name)
        if device['state'] != 'Booted':
            launchd.fail('simulator must be booted to check its features (it is {})'.format(
                device['state']), **launchd.device_summary(device))
            return
        disabled = launchd.read_disabled(device)
        diagnosis = catalog.diagnose_features(required, disabled)
    except catalog.ProfileError as exc:
        launchd.fail(str(exc))
        return
    except launchd.SlimError as exc:
        launchd.fail(str(exc))
        return

    broken = [entry for entry in diagnosis['features'] if not entry['ok']]
    result = {
        'success': True,
        'ok': diagnosis['ok'],
        'features': diagnosis['features'],
        'summary': '{}/{} required features OK'.format(
            len(diagnosis['features']) - len(broken), len(diagnosis['features'])),
    }
    if broken:
        # Point at the fix rather than just the failure: the profile has to
        # keep these daemons, or the simulator has to go back to stock.
        result['remedy'] = ('re-slim keeping the daemons these features need, e.g. '
                            'sim-slim.py --keep {}'.format(
                                ','.join(sorted({label for entry in broken
                                                 for label in entry['disabled']}))))
    result.update(launchd.device_summary(device))
    print(json.dumps(result))
    sys.exit(0 if diagnosis['ok'] else 1)


if __name__ == '__main__':
    main()
