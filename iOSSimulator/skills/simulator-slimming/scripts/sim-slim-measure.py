#!/usr/bin/env python3
"""
Measure what a booted simulator actually costs in memory.

This sums phys_footprint across every process under the simulator's
launchd_sim - the same figure Activity Monitor's Memory column shows. It counts
compressed and swapped pages, so it stays honest under memory pressure where
resident size reads misleadingly low, and it is the number that decides how many
simulators fit before the Mac starts swapping.

Summing `ps` RSS instead would double-count: RSS charges shared mappings to
every process that maps them.

Usage:
    sim-slim-measure.py [--udid <udid>]
    sim-slim-measure.py --all
    sim-slim-measure.py --processes [--limit 20]

Options:
    --udid <udid>   Simulator to measure (defaults to the booted one)
    --name <name>   Simulator to measure, by name
    --all           Measure every booted simulator, plus a fleet total
    --processes     List the heaviest processes in the simulator's tree
    --limit <n>     How many processes to list (default 20)

Output:
    JSON object on stdout.
"""

import argparse
import json
import re
import subprocess

import slim_launchd as launchd

TOP_MEM_LINE = re.compile(r'^\s*(\d+)\s+([0-9.]+[KMGB+]?)')


def launchd_pid(udid):
    """The host PID of the simulator's launchd_sim, the root of its process tree."""
    result = subprocess.run(
        ['pgrep', '-f', '{}/data/var/run/launchd_bootstrap'.format(udid)],
        capture_output=True, text=True)
    pids = result.stdout.split()
    if result.returncode != 0 or not pids:
        raise launchd.SlimError('simulator {} does not appear to be booted'.format(udid))
    return int(pids[0])


def process_snapshot():
    """One ps sweep: parent links, cpu, and command name for every process."""
    result = subprocess.run(['ps', '-axo', 'pid,ppid,%cpu,comm'],
                            capture_output=True, text=True)
    children, cpu, comm = {}, {}, {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        try:
            pid, ppid = int(fields[0]), int(fields[1])
        except ValueError:
            continue
        children.setdefault(ppid, []).append(pid)
        try:
            cpu[pid] = float(fields[2])
        except ValueError:
            cpu[pid] = 0.0
        # comm is the full executable path; basename it so the drill-down shows
        # real daemon names like backboardd or SpringBoard.
        comm[pid] = ' '.join(fields[3:]).rsplit('/', 1)[-1]
    return children, cpu, comm


def parse_bytes(value):
    value = value.strip().rstrip('+')
    if not value:
        return 0
    multiplier = 1
    if value[-1] == 'K':
        multiplier, value = 1024, value[:-1]
    elif value[-1] == 'M':
        multiplier, value = 1024 ** 2, value[:-1]
    elif value[-1] == 'G':
        multiplier, value = 1024 ** 3, value[:-1]
    elif value[-1] == 'B':
        value = value[:-1]
    try:
        return int(float(value) * multiplier)
    except ValueError:
        return 0


def footprint_by_pid():
    result = subprocess.run(['top', '-l', '1', '-stats', 'pid,mem'],
                            capture_output=True, text=True)
    footprints = {}
    for line in result.stdout.splitlines():
        match = TOP_MEM_LINE.match(line)
        if match:
            footprints[int(match.group(1))] = parse_bytes(match.group(2))
    return footprints


def tree_pids(root, children):
    seen, stack = set(), [root]
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children.get(pid, []))
    return seen


def measure(device, children, cpu, footprints):
    pids = tree_pids(launchd_pid(device['udid']), children)
    total_bytes = sum(footprints.get(pid, 0) for pid in pids)
    entry = launchd.device_summary(device)
    entry['processes'] = len(pids)
    entry['bytes'] = total_bytes
    entry['megabytes'] = round(total_bytes / (1024 ** 2), 1)
    # ps reports a decaying average per process, so a busy multicore tree can
    # sum past 100%.
    entry['cpu_percent'] = round(sum(cpu.get(pid, 0.0) for pid in pids), 1)
    return entry, pids


def main():
    parser = argparse.ArgumentParser(description='Measure a booted simulator\'s memory footprint')
    parser.add_argument('--udid', help='Simulator UDID (defaults to the booted one)')
    parser.add_argument('--name', help='Simulator name')
    parser.add_argument('--all', action='store_true', help='Measure every booted simulator')
    parser.add_argument('--processes', action='store_true', help='List the heaviest processes')
    parser.add_argument('--limit', type=int, default=20, help='How many processes to list')
    args = parser.parse_args()

    try:
        # One ps and one top sweep serve every simulator, so measuring a whole
        # fleet costs the same as measuring one.
        children, cpu, comm = process_snapshot()
        footprints = footprint_by_pid()

        if args.all:
            devices = [d for d in launchd.list_devices() if d['state'] == 'Booted']
            measured, errors = [], []
            for device in devices:
                try:
                    entry, _ = measure(device, children, cpu, footprints)
                    measured.append(entry)
                except launchd.SlimError as exc:
                    errors.append(dict(launchd.device_summary(device), error=str(exc)))
            total = sum(entry['bytes'] for entry in measured)
            result = {
                'success': True,
                'simulators': measured,
                'total_bytes': total,
                'total_megabytes': round(total / (1024 ** 2), 1),
            }
            if errors:
                result['unmeasured'] = errors
            print(json.dumps(result))
            return

        device = launchd.resolve_device(args.udid, args.name)
        entry, pids = measure(device, children, cpu, footprints)
        result = {'success': True}
        result.update(entry)

        if args.processes:
            processes = [{
                'pid': pid,
                'command': comm.get(pid, '?'),
                'bytes': footprints.get(pid, 0),
                'megabytes': round(footprints.get(pid, 0) / (1024 ** 2), 1),
                'cpu_percent': cpu.get(pid, 0.0),
            } for pid in pids]
            processes.sort(key=lambda item: (-item['bytes'], item['pid']))
            result['top_processes'] = processes[:args.limit]

        print(json.dumps(result))
    except launchd.SlimError as exc:
        launchd.fail(str(exc))


if __name__ == '__main__':
    main()
