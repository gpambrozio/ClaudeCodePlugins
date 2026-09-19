#!/usr/bin/env python3
"""
launchd plumbing for simulator slimming.

Slimming is `launchctl disable system/<label>` run inside the simulator through
`simctl spawn`. The overrides live in that one simulator's launchd database, so
nothing on the host Mac is touched and each simulator is independent.

The mechanics ported here come from simslim
(https://github.com/MobAI-App/simslim, MIT, Copyright (c) 2026 Interlap); the
comments explain the parts that are non-obvious enough to break if reimplemented
naively.
"""

import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Sequence, Set, Tuple

# A full slim boots the simulator, walks ~170 labels, then reboots. Shared CI
# runners are slow and unpredictable enough to blow a tight budget mid-way, so
# the ceiling is generous and raisable rather than clever.
DEFAULT_BOOT_TIMEOUT = int(os.environ.get('SIM_SLIM_BOOT_TIMEOUT', '600'))
# One launchctl transition. Right after a first boot the simulator is saturated
# by its own startup work and a single spawn can stall for minutes; bounding it
# turns one stuck label into a retry instead of a lost reconfigure.
DEFAULT_SPAWN_TIMEOUT = int(os.environ.get('SIM_SLIM_SPAWN_TIMEOUT', '120'))
SHUTDOWN_TIMEOUT = 60

# How many launchctl transitions run at once. Each one is an independent
# launchd write, so they parallelize cleanly, and a full slim is ~170 of them:
# serially that is several minutes, concurrently well under one. The work is
# spawn-latency bound rather than CPU bound, so a modest pool captures nearly
# all of the win without swamping a simulator that is still settling after boot.
#
# Concurrency lives here on the host rather than in a shell script inside the
# simulator, because `simctl spawn <udid> /bin/sh` fails outright on some
# runtimes ("Invalid or missing Program/ProgramArguments") - `launchctl` as the
# direct spawn target is the only form that works everywhere.
APPLY_WORKERS = 8
# Disables persist, so each later pass only retries what earlier passes failed.
APPLY_PASSES = 3

# `launchctl bootout` exits 3 when the job is not loaded, which is already the
# state a live disable wants.
BOOTOUT_GONE = 3

# Device sets simctl commands may target. "" is the default set; Xcode's
# parallel-testing clones live in "testing".
KNOWN_SETS = [('', 'default'), ('testing', 'testing')]


class SlimError(Exception):
    """An operation failed in a way the caller should report and stop on."""


class Deadline:
    """A wall-clock budget for a multi-step reconfigure."""

    def __init__(self, seconds: int):
        self.seconds = seconds
        self.start = time.time()

    def remaining(self) -> float:
        return self.seconds - (time.time() - self.start)

    def expired(self) -> bool:
        return self.remaining() <= 0

    def check(self, what: str) -> None:
        if self.expired():
            raise SlimError(
                '{} exceeded the {}s budget; raise it with --boot-timeout or '
                'SIM_SLIM_BOOT_TIMEOUT (slow CI runners often need 900 or more)'.format(
                    what, self.seconds))


def _run(args: Sequence[str], timeout: Optional[float] = None) -> Tuple[int, str]:
    """Run a command, returning (exit code, combined output)."""
    code, stdout, stderr = _run_split(args, timeout)
    return code, stdout + stderr


def _run_split(args: Sequence[str], timeout: Optional[float] = None) -> Tuple[int, str, str]:
    """Run a command, keeping stdout and stderr apart.

    simctl happily writes warnings to stderr while printing valid JSON to
    stdout, so anything that parses output has to read the two separately.
    """
    try:
        result = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, '', 'timed out after {}s'.format(timeout)
    return result.returncode, result.stdout or '', result.stderr or ''


def simctl_args(set_token: str, *sub: str) -> List[str]:
    """Build an xcrun simctl argument list; --set must precede the subcommand."""
    if set_token:
        return ['xcrun', 'simctl', '--set', set_token] + list(sub)
    return ['xcrun', 'simctl'] + list(sub)


def _os_version(runtime: str) -> str:
    """'com.apple.CoreSimulator.SimRuntime.iOS-26-5' -> '26.5'."""
    marker = 'iOS-'
    index = runtime.rfind(marker)
    if index < 0:
        return '?'
    return runtime[index + len(marker):].replace('-', '.')


def _list_devices_in_set(set_token: str, set_name: str) -> List[dict]:
    code, stdout, stderr = _run_split(simctl_args(set_token, 'list', 'devices', '-j'), timeout=60)
    if code != 0:
        if 'unable to find utility "simctl"' in stderr:
            raise SlimError(
                'simctl is unavailable: it ships with full Xcode, not the Command Line '
                'Tools. Select an Xcode with `sudo xcode-select -s /Applications/Xcode.app`.')
        raise SlimError('simctl list failed: {}'.format((stdout + stderr).strip()))

    try:
        listing = json.loads(stdout)
    except ValueError as exc:
        raise SlimError('could not parse simctl list output: {}'.format(exc))

    devices = []
    for runtime, entries in listing.get('devices', {}).items():
        if 'iOS' not in runtime:
            continue
        for entry in entries:
            if not entry.get('isAvailable', True):
                continue
            devices.append({
                'udid': entry.get('udid'),
                'name': entry.get('name'),
                'state': entry.get('state'),
                'os_version': _os_version(runtime),
                'set': set_name,
                'set_token': set_token,
            })
    return devices


def list_devices() -> List[dict]:
    """List available iOS simulators across the default and testing sets.

    The default set is mandatory; a secondary set that cannot be listed (it may
    simply not exist) is skipped rather than failing the whole listing.
    """
    devices = []
    for set_token, set_name in KNOWN_SETS:
        try:
            devices.extend(_list_devices_in_set(set_token, set_name))
        except SlimError:
            if not set_token:
                raise
    return devices


def resolve_device(udid: Optional[str] = None, name: Optional[str] = None) -> dict:
    """Find the simulator to operate on.

    With neither udid nor name, this picks the booted simulator - the same
    default the rest of the iOS Simulator scripts use. Slimming is a
    per-simulator, reboot-inducing change, so an ambiguous choice is refused
    rather than guessed at.
    """
    devices = list_devices()

    if udid:
        for device in devices:
            if device['udid'] == udid:
                return device
        raise SlimError('no available simulator with UDID {}'.format(udid))

    if name:
        matches = [device for device in devices if device['name'] == name]
        if not matches:
            raise SlimError('no available simulator named "{}"'.format(name))
        matches.sort(key=lambda device: device['os_version'], reverse=True)
        return matches[0]

    booted = [device for device in devices if device['state'] == 'Booted']
    if not booted:
        raise SlimError('no booted simulator found; boot one first or pass --udid/--name')
    if len(booted) > 1:
        names = ', '.join('{} ({})'.format(d['name'], d['udid']) for d in booted)
        raise SlimError(
            'several simulators are booted, so the target is ambiguous; '
            'pass --udid to choose one of: {}'.format(names))
    return booted[0]


def supports_persistent_overrides(os_version: str) -> bool:
    """Does this runtime keep disable overrides across a reboot?

    iOS 17.x and 18.3 accept every `launchctl disable` and then come back stock,
    which looks like success but silently leaves a heavy simulator. iOS 18.5 is
    the earliest runtime verified to persist them.
    """
    parts = os_version.split('.')
    if len(parts) < 2:
        return False
    try:
        major, minor = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    return major > 18 or (major == 18 and minor >= 5)


def boot_and_wait(device: dict, deadline: Deadline) -> None:
    """Boot the device (tolerating an already-booted one) and wait for its services."""
    deadline.check('boot')
    code, output = _run(simctl_args(device['set_token'], 'boot', device['udid']),
                        timeout=max(deadline.remaining(), 1))
    if code != 0 and 'already booted' not in output and 'current state: Booted' not in output:
        raise SlimError('simctl boot failed: {}'.format(output.strip()))

    deadline.check('boot')
    code, output = _run(simctl_args(device['set_token'], 'bootstatus', device['udid'], '-b'),
                        timeout=max(deadline.remaining(), 1))
    if code != 0:
        raise SlimError('simctl bootstatus failed: {}'.format(output.strip()))


def shutdown_and_wait(device: dict, deadline: Deadline) -> None:
    deadline.check('shutdown')
    code, output = _run(simctl_args(device['set_token'], 'shutdown', device['udid']),
                        timeout=max(deadline.remaining(), 1))
    if code != 0 and 'current state: Shutdown' not in output:
        raise SlimError('simctl shutdown failed: {}'.format(output.strip()))

    waited = 0.0
    while waited < SHUTDOWN_TIMEOUT:
        if device_state(device) == 'Shutdown':
            return
        time.sleep(0.5)
        waited += 0.5
    raise SlimError('timed out waiting for {} to shut down'.format(device['udid']))


def device_state(device: dict) -> str:
    for entry in _list_devices_in_set(device['set_token'], device['set']):
        if entry['udid'] == device['udid']:
            return entry['state']
    raise SlimError('simulator {} disappeared from the device list'.format(device['udid']))


def read_disabled(device: dict, timeout: Optional[float] = None) -> Set[str]:
    """Labels currently disabled in the simulator's system domain.

    A label absent from the output is enabled.
    """
    code, output = _run(
        simctl_args(device['set_token'], 'spawn', device['udid'],
                    'launchctl', 'print-disabled', 'system'),
        timeout=timeout or DEFAULT_SPAWN_TIMEOUT)
    if code != 0:
        raise SlimError('launchctl print-disabled failed: {}'.format(output.strip()))
    return parse_disabled(output)


# Recent launchd prints `"com.apple.x" => disabled`; older builds print
# `=> true` / `=> false`, so both spellings count.
_DISABLED_LINE = re.compile(r'"([^"]+)"\s*=>\s*(\S+)')


def parse_disabled(output: str) -> Set[str]:
    disabled = set()
    for match in _DISABLED_LINE.finditer(output):
        label, value = match.group(1), match.group(2)
        if value.startswith('disabled') or value.startswith('true'):
            disabled.add(label)
    return disabled


def _launchctl(device: dict, verb: str, label: str, spawn_timeout: int) -> Tuple[int, str]:
    return _run(simctl_args(device['set_token'], 'spawn', device['udid'],
                            'launchctl', verb, 'system/' + label),
                timeout=spawn_timeout)


def _transition(device: dict, action: str, label: str, spawn_timeout: int) -> Optional[str]:
    """Apply one transition; return None on success or a message describing the failure.

    launchctl exits 0 even when it prints its benign "switch to
    user/foreground" note, so a non-zero exit is a real failure.
    """
    verb = 'disable' if action == 'bootout' else action
    code, output = _launchctl(device, verb, label, spawn_timeout)
    if code != 0:
        return '{} {}: {}'.format(verb, label, output.strip())
    if action != 'bootout':
        return None
    # A disable override only blocks the next bootstrap, so a live slim has to
    # evict the running job too. Booting out a job that is already gone is the
    # state we want, which is what keeps this idempotent.
    code, output = _launchctl(device, 'bootout', label, spawn_timeout)
    if code not in (0, BOOTOUT_GONE):
        return 'bootout {}: {}'.format(label, output.strip())
    return None


def apply_delta(device: dict, to_disable: Sequence[str], to_enable: Sequence[str],
                disable_action: str, deadline: Deadline, spawn_timeout: int,
                progress=None) -> None:
    """Apply launchd transitions concurrently, retrying whatever fails.

    disable_action is 'disable' (override only, takes effect at the next boot)
    or 'bootout' (disable, then evict the running job so it stops now).

    Failures are collected and retried on later passes instead of aborting the
    run: the first pass races the simulator's own startup work, and a label that
    times out once usually succeeds seconds later once the device has settled.
    """
    def report(message: str) -> None:
        if progress is not None:
            progress(message)

    pending = [(disable_action, label) for label in to_disable]
    pending += [('enable', label) for label in to_enable]
    total = len(pending)
    if not total:
        return

    done = 0
    failures = []
    for pass_number in range(1, APPLY_PASSES + 1):
        if not pending:
            break
        if pass_number > 1:
            report('retrying {} service(s), pass {}/{}'.format(
                len(pending), pass_number, APPLY_PASSES))
        deadline.check('applying launchd overrides')

        failed = []
        failures = []
        workers = min(APPLY_WORKERS, len(pending))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_transition, device, action, label, spawn_timeout): (action, label)
                for action, label in pending
            }
            for future in as_completed(futures):
                action, label = futures[future]
                error = future.result()
                if error:
                    failed.append((action, label))
                    failures.append(error)
                    continue
                done += 1
                if done == total or done % 20 == 0:
                    report('{}/{} services updated'.format(done, total))
        pending = failed

    if pending:
        raise SlimError(
            '{}/{} launchd transitions failed after {} passes: {}'.format(
                len(pending), total, APPLY_PASSES, '; '.join(failures[:5])))


def ensure_overrides(device: dict, desired: Set[str], managed: Set[str], deadline: Deadline,
                     spawn_timeout: int, progress=None) -> Tuple[bool, Set[str], dict]:
    """Bring the simulator to exactly `desired` and reboot it into that state.

    Both slimming and un-slimming are this same operation - un-slimming is just
    an empty desired set - so they share one implementation and one set of
    guarantees: only managed labels move, the reboot is skipped when nothing
    changed, and the result is read back afterwards rather than assumed.
    """
    def report(message: str) -> None:
        if progress is not None:
            progress(message)

    report('booting the simulator (a first boot can take a minute)')
    boot_and_wait(device, deadline)

    current = read_disabled(device, spawn_timeout)
    to_disable = sorted(label for label in desired if label in managed and label not in current)
    to_enable = sorted(label for label in current if label in managed and label not in desired)
    if not to_disable and not to_enable:
        return False, current, {'disabled': 0, 're_enabled': 0}

    if to_disable:
        report('disabling {} background service(s)'.format(len(to_disable)))
    if to_enable:
        report('re-enabling {} background service(s)'.format(len(to_enable)))
    apply_delta(device, to_disable, to_enable, 'disable', deadline, spawn_timeout, progress)

    report('rebooting to apply the changes')
    shutdown_and_wait(device, deadline)
    boot_and_wait(device, deadline)

    after = read_disabled(device, spawn_timeout)
    lost = [label for label in desired if label in managed and label not in after]
    lost += [label for label in after if label in managed and label not in desired]
    if lost:
        raise SlimError(
            '{} override(s) did not survive the reboot; this runtime may not persist them'.format(
                len(lost)))
    return True, after, {'disabled': len(to_disable), 're_enabled': len(to_enable)}


def device_summary(device: dict) -> dict:
    """The device fields every script echoes back, so output is comparable."""
    return {
        'udid': device['udid'],
        'name': device['name'],
        'os_version': device['os_version'],
        'set': device['set'],
    }


def fail(message: str, **extra) -> None:
    """Print a JSON error object and exit non-zero."""
    import sys
    payload = {'success': False, 'error': message}
    payload.update(extra)
    print(json.dumps(payload))
    sys.exit(1)
