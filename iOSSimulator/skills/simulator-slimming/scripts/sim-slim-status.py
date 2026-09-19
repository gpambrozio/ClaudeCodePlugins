#!/usr/bin/env python3
"""
Report how slim an iOS Simulator currently is.

This counts managed launchd labels that are disabled - not running processes. A
slim simulator still runs required core services, system apps, and extensions,
so use sim-slim-measure.py when the question is "how much memory is this
costing me?" and this when the question is "is my slimming still applied?".

Usage:
    sim-slim-status.py [--udid <udid>] [--dropped]
    sim-slim-status.py --all

Options:
    --udid <udid>  Simulator to inspect (defaults to the booted one)
    --name <name>  Simulator to inspect, by name
    --all          Report every booted simulator
    --dropped      List the disabled labels grouped by category, with downsides

Output:
    JSON object on stdout.
"""

import argparse
import json

import slim_catalog as catalog
import slim_launchd as launchd


def status_for(device, slimmable, dropped):
    entry = launchd.device_summary(device)
    entry['booted'] = device['state'] == 'Booted'
    entry['managed_total'] = len(slimmable)
    entry['persistent'] = launchd.supports_persistent_overrides(device['os_version'])

    if not entry['booted']:
        # The overrides live inside the simulator's launchd, which only exists
        # while it is booted, so there is nothing to read yet.
        entry['error'] = 'simulator must be booted to read its state (it is {})'.format(
            device['state'])
        return entry

    disabled = launchd.read_disabled(device)
    managed_disabled = disabled & slimmable
    entry['disabled_count'] = len(managed_disabled)
    entry['slim'] = bool(managed_disabled)
    if not entry['persistent']:
        entry['note'] = ('iOS {} does not persist disable overrides across a reboot, so this '
                         'state lasts only for the current boot session'.format(
                             device['os_version']))
    if dropped:
        entry['dropped'] = catalog.affected_categories(managed_disabled)
    return entry


def main():
    parser = argparse.ArgumentParser(description='Report iOS Simulator slimming status')
    parser.add_argument('--udid', help='Simulator UDID (defaults to the booted one)')
    parser.add_argument('--name', help='Simulator name')
    parser.add_argument('--all', action='store_true', help='Report every booted simulator')
    parser.add_argument('--dropped', action='store_true',
                        help='List disabled labels grouped by category')
    args = parser.parse_args()

    slimmable = catalog.slimmable_labels()

    try:
        if args.all:
            devices = [d for d in launchd.list_devices() if d['state'] == 'Booted']
            if not devices:
                print(json.dumps({'success': True, 'simulators': [],
                                  'message': 'no simulators are booted'}))
                return
            simulators = [status_for(device, slimmable, args.dropped) for device in devices]
            print(json.dumps({'success': True, 'simulators': simulators}))
            return

        device = launchd.resolve_device(args.udid, args.name)
        result = {'success': True}
        result.update(status_for(device, slimmable, args.dropped))
        print(json.dumps(result))
    except launchd.SlimError as exc:
        launchd.fail(str(exc))


if __name__ == '__main__':
    main()
