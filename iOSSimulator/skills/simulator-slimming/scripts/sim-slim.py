#!/usr/bin/env python3
"""
Slim an iOS Simulator: disable the background daemons it does not need.

A stock simulator boots ~180 background services - Siri, Spotlight indexing,
photo analysis, News, wallpaper posters, iCloud sync - none of which matter for
development, UI automation, or CI. Turning them off cuts a simulator's memory
roughly 4x, which is what decides how many simulators fit on one Mac.

Usage:
    sim-slim.py [--udid <udid>] [--except <ids>] [--keep <labels>]
    sim-slim.py --profile ci.json [--udid <udid>]
    sim-slim.py --no-reboot [--udid <udid>]
    sim-slim.py --dry-run

Options:
    --udid <udid>        Simulator to slim (defaults to the booted one)
    --name <name>        Simulator to slim, by name
    --except <ids>       Comma-separated category IDs to leave fully enabled
    --keep <labels>      Comma-separated launchd labels to leave enabled
    --profile <path>     JSON profile file; cannot be combined with --except/--keep
    --no-reboot          Slim the running boot session in place, without a reboot
    --dry-run            Report what would change; touch nothing
    --boot-timeout <s>   Budget for the whole operation (default 600)
    --spawn-timeout <s>  Budget for one launchctl transition (default 120)
    --quiet              Do not write progress to stderr

Output:
    JSON object on stdout; human-readable progress on stderr.
"""

import argparse
import json
import sys
import time

import slim_catalog as catalog
import slim_launchd as launchd


def build_progress(quiet):
    def progress(message):
        if not quiet:
            sys.stderr.write('  {}\n'.format(message))
            sys.stderr.flush()
    return progress


def dry_run(device, profile, managed):
    """Report the plan without booting or changing anything."""
    result = {
        'success': True,
        'mode': 'dry-run',
        'changed': False,
        'persistent': launchd.supports_persistent_overrides(device['os_version']),
        'profile': {'except': profile['except'], 'keep': profile['keep']},
        'would_disable_total': len(profile['desired']),
        'managed_total': len(managed),
        'categories_affected': catalog.affected_categories(profile['desired']),
    }
    result.update(launchd.device_summary(device))

    if device['state'] == 'Booted':
        current = launchd.read_disabled(device)
        to_disable, to_enable = catalog.delta(current, profile['desired'], managed)
        result['already_disabled'] = len(current & managed)
        result['would_disable'] = to_disable
        result['would_re_enable'] = to_enable
        result['changed'] = bool(to_disable or to_enable)
    else:
        result['note'] = ('the simulator is shut down, so its current overrides cannot be '
                          'read; boot it to see the exact transitions')
    return result


def slim_without_reboot(device, profile, managed, deadline, spawn_timeout, progress):
    """Disable and evict the daemons in the running boot session.

    Every profiled label is booted out, not just the ones lacking an override:
    an override says nothing about whether the job is still loaded, and a
    bootout of an already-gone job is a cheap no-op. That keeps the command
    idempotent.
    """
    progress('booting the simulator (a first boot can take a minute)')
    launchd.boot_and_wait(device, deadline)

    current = launchd.read_disabled(device, spawn_timeout)
    to_disable, extra = catalog.delta(current, profile['desired'], managed)

    warnings = []
    if extra:
        # Re-enabling live would mean bootstrapping each job again, so a live
        # slim only ever moves toward more-disabled. `sim-slim-off.py` restores
        # them with a reboot.
        warnings.append(
            '{} managed service(s) are disabled beyond this profile and were left alone; '
            'only sim-slim-off.py re-enables them'.format(len(extra)))

    labels = sorted(label for label in profile['desired'] if label in managed)
    progress('stopping {} background service(s) for this boot session'.format(len(labels)))
    launchd.apply_delta(device, labels, [], 'bootout', deadline, spawn_timeout, progress)

    after = launchd.read_disabled(device, spawn_timeout)
    missing, _ = catalog.delta(after, profile['desired'], managed)
    if missing:
        raise launchd.SlimError(
            '{} of {} disable override(s) did not take'.format(len(missing), len(labels)))
    return bool(to_disable), after, {'disabled': len(to_disable), 're_enabled': 0}, warnings


def main():
    parser = argparse.ArgumentParser(description='Slim an iOS Simulator')
    parser.add_argument('--udid', help='Simulator UDID (defaults to the booted one)')
    parser.add_argument('--name', help='Simulator name')
    parser.add_argument('--except', dest='except_ids', default='',
                        help='Comma-separated category IDs to leave fully enabled')
    parser.add_argument('--keep', default='',
                        help='Comma-separated launchd labels to leave enabled')
    parser.add_argument('--profile', help='Path to a JSON profile file')
    parser.add_argument('--no-reboot', action='store_true',
                        help='Slim the current boot session in place')
    parser.add_argument('--dry-run', action='store_true', help='Report the plan, change nothing')
    parser.add_argument('--boot-timeout', type=int, default=launchd.DEFAULT_BOOT_TIMEOUT,
                        help='Seconds budgeted for the whole operation')
    parser.add_argument('--spawn-timeout', type=int, default=launchd.DEFAULT_SPAWN_TIMEOUT,
                        help='Seconds budgeted for one launchctl transition')
    parser.add_argument('--quiet', action='store_true', help='No progress output on stderr')
    args = parser.parse_args()

    progress = build_progress(args.quiet)
    started = time.time()

    try:
        profile = catalog.build_profile(
            catalog.parse_list(args.except_ids), catalog.parse_list(args.keep), args.profile)
    except catalog.ProfileError as exc:
        launchd.fail(str(exc))
        return

    managed = catalog.managed_labels()

    try:
        device = launchd.resolve_device(args.udid, args.name)
    except launchd.SlimError as exc:
        launchd.fail(str(exc))
        return

    if args.dry_run:
        try:
            print(json.dumps(dry_run(device, profile, managed)))
        except launchd.SlimError as exc:
            launchd.fail(str(exc), **launchd.device_summary(device))
        return

    persistent = launchd.supports_persistent_overrides(device['os_version'])
    if profile['desired'] and not args.no_reboot and not persistent:
        launchd.fail(
            'iOS {} cannot persist launchd disable overrides across a reboot (iOS 18.5 is the '
            'earliest runtime that can). Use --no-reboot to slim the current boot session, and '
            're-run it after every boot.'.format(device['os_version']),
            **launchd.device_summary(device))
        return

    deadline = launchd.Deadline(args.boot_timeout)
    warnings = []
    try:
        if args.no_reboot:
            changed, disabled, applied, warnings = slim_without_reboot(
                device, profile, managed, deadline, args.spawn_timeout, progress)
        else:
            changed, disabled, applied = launchd.ensure_overrides(
                device, profile['desired'], managed, deadline, args.spawn_timeout, progress)
    except launchd.SlimError as exc:
        launchd.fail(str(exc), **launchd.device_summary(device))
        return

    if args.no_reboot and not persistent:
        warnings.append(
            'iOS {} does not persist these overrides: the simulator comes back stock at its '
            'next boot, so re-run this after every boot.'.format(device['os_version']))

    result = {
        'success': True,
        'mode': 'no-reboot' if args.no_reboot else 'reboot',
        'changed': changed,
        'persistent': persistent,
        'profile': {'except': profile['except'], 'keep': profile['keep']},
        'applied': applied,
        'disabled_total': len(disabled & managed),
        'managed_total': len(managed),
        'categories_affected': catalog.affected_categories(disabled),
        'elapsed_seconds': round(time.time() - started, 1),
    }
    if warnings:
        result['warnings'] = warnings
    if not changed:
        result['message'] = 'already in the requested slim state; nothing to do'
    result.update(launchd.device_summary(device))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
