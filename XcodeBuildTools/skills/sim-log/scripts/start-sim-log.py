#!/usr/bin/env python3
"""
Start capturing logs from an iOS simulator.

Usage:
    start-sim-log.py --udid SIMULATOR_UDID --bundle-id com.example.MyApp [--output /path/to/log.txt]

Arguments:
    --udid UDID           Simulator UDID (from sim-list.py or xcrun simctl list)
    --bundle-id BUNDLE    Bundle identifier of the app to capture logs for
    --output PATH         Optional file path to write logs (default: stdout)
    --level LEVEL         Log level filter: default, info, debug (default: default)

Output:
    Streams logs to stdout or file. Press Ctrl+C to stop.
"""

import argparse
import json
import re
import subprocess
import sys


def get_app_name_from_bundle_id(udid, bundle_id):
    """Get the app name (CFBundleName) for a bundle ID from installed simulator apps."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "listapps", udid],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return None

        output = result.stdout
        # Parse the plist-style output to find CFBundleName for our bundle ID
        # Look for pattern: CFBundleIdentifier = "bundle_id"; ... CFBundleName = AppName;
        # The output groups apps by bundle ID, so we find our bundle section first

        # Find the section for our bundle ID
        pattern = rf'"{re.escape(bundle_id)}"\s*=\s*\{{'
        match = re.search(pattern, output)
        if not match:
            return None

        # Find the CFBundleName within this app's section (before the next app section)
        start_pos = match.end()
        # Look for CFBundleName in this section
        remaining = output[start_pos:]
        name_match = re.search(r'CFBundleName\s*=\s*"?([^";]+)"?\s*;', remaining)
        if name_match:
            return name_match.group(1).strip()

        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Start capturing simulator logs")
    parser.add_argument("--udid", required=True, help="Simulator UDID")
    parser.add_argument("--bundle-id", required=True, help="Bundle identifier of the app")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--level", choices=["default", "info", "debug"], default="default",
                        help="Log level filter")

    args = parser.parse_args()

    # Get the actual app name from the simulator's installed apps
    app_name = get_app_name_from_bundle_id(args.udid, args.bundle_id)
    if not app_name:
        # Fall back to last component of bundle ID (less reliable)
        app_name = args.bundle_id.split(".")[-1]

    # Build predicate to filter logs by bundle ID (subsystem) or process name
    predicate = f'subsystem == "{args.bundle_id}" OR process == "{app_name}"'

    cmd = [
        "xcrun", "simctl", "spawn", args.udid,
        "log", "stream",
        "--predicate", predicate,
        "--style", "compact",
        "--level", args.level
    ]

    output_file = None
    try:
        if args.output:
            output_file = open(args.output, 'w')
            target = output_file
            # Print status to stderr so it doesn't go to the log file
            sys.stderr.write(json.dumps({
                "success": True,
                "message": f"Started log capture for {args.bundle_id}",
                "simulator": args.udid,
                "output_file": args.output,
                "hint": "Press Ctrl+C to stop capture"
            }) + "\n")
        else:
            target = sys.stdout
            # Print initial message to stderr
            sys.stderr.write(json.dumps({
                "success": True,
                "message": f"Started log capture for {args.bundle_id}",
                "simulator": args.udid,
                "hint": "Press Ctrl+C to stop capture"
            }) + "\n")

        # Run log stream
        process = subprocess.Popen(
            cmd,
            stdout=target,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for process or Ctrl+C
        process.wait()

    except KeyboardInterrupt:
        if output_file:
            output_file.close()
        sys.stderr.write(json.dumps({
            "success": True,
            "message": "Log capture stopped"
        }) + "\n")
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)
    finally:
        if output_file:
            output_file.close()


if __name__ == "__main__":
    main()
