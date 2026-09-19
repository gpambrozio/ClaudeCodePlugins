#!/usr/bin/env python3
"""
Restore a slimmed iOS Simulator to stock: re-enable every managed daemon.

Use this when a simulator needs a capability slimming took away and narrowing
the profile is not enough - or simply to hand a simulator back in the state
Xcode expects. The simulator reboots, since re-enabling a daemon only takes
effect at the next boot.

Usage:
    sim-slim-off.py [--udid <udid>] [--name <name>]

Options:
    --udid <udid>        Simulator to restore (defaults to the booted one)
    --name <name>        Simulator to restore, by name
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


def main():
    parser = argparse.ArgumentParser(description='Restore a slimmed iOS Simulator to stock')
    parser.add_argument('--udid', help='Simulator UDID (defaults to the booted one)')
    parser.add_argument('--name', help='Simulator name')
    parser.add_argument('--boot-timeout', type=int, default=launchd.DEFAULT_BOOT_TIMEOUT,
                        help='Seconds budgeted for the whole operation')
    parser.add_argument('--spawn-timeout', type=int, default=launchd.DEFAULT_SPAWN_TIMEOUT,
                        help='Seconds budgeted for one launchctl transition')
    parser.add_argument('--quiet', action='store_true', help='No progress output on stderr')
    args = parser.parse_args()

    def progress(message):
        if not args.quiet:
            sys.stderr.write('  {}\n'.format(message))
            sys.stderr.flush()

    started = time.time()
    managed = catalog.managed_labels()

    try:
        device = launchd.resolve_device(args.udid, args.name)
        deadline = launchd.Deadline(args.boot_timeout)
        changed, disabled, applied = launchd.ensure_overrides(
            device, set(), managed, deadline, args.spawn_timeout, progress)
    except launchd.SlimError as exc:
        launchd.fail(str(exc))
        return

    result = {
        'success': True,
        'changed': changed,
        'applied': applied,
        'disabled_total': len(disabled & managed),
        'managed_total': len(managed),
        'elapsed_seconds': round(time.time() - started, 1),
    }
    result['message'] = ('restored to stock' if changed
                         else 'already stock; no managed services were disabled')
    result.update(launchd.device_summary(device))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
