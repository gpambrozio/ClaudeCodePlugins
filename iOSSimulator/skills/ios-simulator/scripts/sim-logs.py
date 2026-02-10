#!/usr/bin/env python3
"""
Stream and filter iOS Simulator logs.

Monitor app or system logs with severity filtering, deduplication,
and token-efficient summaries.

Usage:
    sim-logs.py --bundle-id <id> --duration 30s
    sim-logs.py --bundle-id <id> --follow
    sim-logs.py --severity error,warning --duration 10s
    sim-logs.py --duration 5s --output /tmp/logs

Options:
    --bundle-id, -b <id>    Filter logs by app bundle ID
    --udid <udid>           Simulator UDID (uses booted if not specified)
    --severity <levels>     Comma-separated: error, warning, info, debug (default: all)
    --duration <time>       Capture duration (e.g., 10s, 2m, 1h)
    --follow                Follow mode - stream logs until Ctrl+C
    --output <dir>          Save full logs and summary to directory
    --verbose               Show full log lines in output

Output:
    JSON object with log statistics, errors, warnings, and sample lines.
    In --follow mode, logs are streamed to stdout in real time.
"""

import json
import re
import signal
import subprocess
import sys
import argparse
from datetime import datetime
from pathlib import Path

from sim_utils import get_booted_simulator_udid


def parse_duration(duration_str):
    """Parse a duration string like '30s', '5m', '1h' into seconds."""
    match = re.match(r'^(\d+)([smh])$', duration_str.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if unit == 's':
        return value
    if unit == 'm':
        return value * 60
    return value * 3600


def classify_severity(line):
    """Classify a log line by severity based on content patterns."""
    lower = line.lower()

    error_patterns = [r'\berror\b', r'\bfault\b', r'\bfailed\b', r'\bexception\b', r'\bcrash\b']
    for p in error_patterns:
        if re.search(p, lower):
            return 'error'

    warning_patterns = [r'\bwarning\b', r'\bwarn\b', r'\bdeprecated\b']
    for p in warning_patterns:
        if re.search(p, lower):
            return 'warning'

    info_patterns = [r'\binfo\b', r'\bnotice\b']
    for p in info_patterns:
        if re.search(p, lower):
            return 'info'

    return 'debug'


def deduplicate_signature(line):
    """Create a signature for deduplication by stripping timestamps and PIDs."""
    sig = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', '', line)
    sig = re.sub(r'\[\d+\]', '', sig)
    return re.sub(r'\s+', ' ', sig).strip()


def stream_logs(udid, bundle_id=None, severity_filter=None, duration=None,
                follow=False, verbose=False):
    """Stream and process simulator logs.

    Returns:
        dict with log statistics and captured data, or None on failure.
    """
    cmd = ['xcrun', 'simctl', 'spawn', udid, 'log', 'stream', '--level', 'debug']

    if bundle_id:
        app_name = bundle_id.split('.')[-1]
        cmd.extend(['--predicate', f'processImagePath CONTAINS "{app_name}"'])

    if severity_filter is None:
        severity_filter = {'error', 'warning', 'info', 'debug'}
    else:
        severity_filter = set(severity_filter)

    # State
    all_lines = []
    errors = []
    warnings = []
    counts = {'error': 0, 'warning': 0, 'info': 0, 'debug': 0, 'total': 0}
    seen = set()
    interrupted = False
    process = None

    def on_signal(sig, frame):
        nonlocal interrupted
        interrupted = True
        if process:
            process.terminate()

    signal.signal(signal.SIGINT, on_signal)

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )

        start = datetime.now()

        for line in iter(process.stdout.readline, ''):
            if not line:
                break

            stripped = line.rstrip()
            if not stripped:
                continue

            counts['total'] += 1
            all_lines.append(stripped)

            severity = classify_severity(stripped)
            counts[severity] += 1

            if severity not in severity_filter:
                continue

            # Deduplicate errors and warnings
            if severity in ('error', 'warning'):
                sig = deduplicate_signature(stripped)
                if sig in seen:
                    continue
                seen.add(sig)

            if severity == 'error':
                errors.append(stripped)
            elif severity == 'warning':
                warnings.append(stripped)

            if follow:
                print(stripped, flush=True)

            if duration and (datetime.now() - start).total_seconds() >= duration:
                break
            if interrupted:
                break

        process.wait()

    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to stream logs: {e}'
        }
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    result = {
        'success': True,
        'bundle_id': bundle_id,
        'udid': udid,
        'statistics': {
            'total_lines': counts['total'],
            'errors': counts['error'],
            'warnings': counts['warning'],
            'info': counts['info'],
            'debug': counts['debug'],
        },
        'errors': errors[:20],
        'warnings': warnings[:20],
    }

    if verbose:
        result['recent_lines'] = all_lines[-50:]

    return result, all_lines


def save_logs(all_lines, result, output_dir, bundle_id):
    """Save logs and summary to the output directory."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    app_name = bundle_id.split('.')[-1] if bundle_id else 'simulator'

    log_file = path / f'{app_name}-{timestamp}.log'
    log_file.write_text('\n'.join(all_lines))

    json_file = path / f'{app_name}-{timestamp}-summary.json'
    json_file.write_text(json.dumps(result, indent=2))

    return str(log_file), str(json_file)


def main():
    parser = argparse.ArgumentParser(description='Stream and filter iOS Simulator logs')
    parser.add_argument('--bundle-id', '-b', help='Filter logs by app bundle ID')
    parser.add_argument('--udid', help='Simulator UDID (uses booted if not specified)')
    parser.add_argument('--severity', help='Comma-separated severity filter (error,warning,info,debug)')

    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--duration', help='Capture duration (e.g., 10s, 2m, 1h)')
    time_group.add_argument('--follow', action='store_true', help='Follow mode (Ctrl+C to stop)')

    parser.add_argument('--output', help='Save logs to this directory')
    parser.add_argument('--verbose', action='store_true', help='Include recent log lines in output')

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

    # Parse duration
    duration = None
    if args.duration:
        duration = parse_duration(args.duration)
        if duration is None:
            print(json.dumps({
                'success': False,
                'error': f"Invalid duration format: '{args.duration}'. Use e.g., 10s, 2m, 1h"
            }))
            sys.exit(1)

    if not args.duration and not args.follow:
        # Default to 10 seconds if neither specified
        duration = 10

    # Parse severity filter
    severity_filter = None
    if args.severity:
        severity_filter = [s.strip().lower() for s in args.severity.split(',')]
        valid = {'error', 'warning', 'info', 'debug'}
        invalid = [s for s in severity_filter if s not in valid]
        if invalid:
            print(json.dumps({
                'success': False,
                'error': f"Invalid severity level(s): {', '.join(invalid)}. Valid: error, warning, info, debug"
            }))
            sys.exit(1)

    # Stream logs
    output = stream_logs(
        udid,
        bundle_id=args.bundle_id,
        severity_filter=severity_filter,
        duration=duration,
        follow=args.follow,
        verbose=args.verbose,
    )

    if isinstance(output, dict):
        # Error case
        print(json.dumps(output))
        sys.exit(1)

    result, all_lines = output

    # Save if requested
    if args.output:
        log_file, json_file = save_logs(all_lines, result, args.output, args.bundle_id)
        result['saved'] = {
            'log_file': log_file,
            'summary_file': json_file,
        }

    if not args.follow:
        print(json.dumps(result, indent=2))

    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
