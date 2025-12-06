#!/usr/bin/env python3
"""
Erase (factory reset) an iOS simulator.

Usage:
    erase-simulator.py --udid SIMULATOR_UDID [--shutdown-first]

Arguments:
    --udid UDID           Simulator UDID to erase
    --shutdown-first      Shutdown the simulator before erasing (required if booted)

Output:
    JSON with erase status
"""

import argparse
import json
import subprocess
import sys


def shutdown_simulator(udid):
    """Shutdown a simulator."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "shutdown", udid],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0 or "Unable to shutdown" in result.stderr
    except Exception:
        return False


def erase_simulator(udid):
    """Erase a simulator."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "erase", udid],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return True, "Simulator erased successfully"
        else:
            error = result.stderr.strip()
            if "Booted" in error:
                return False, "Simulator is booted. Use --shutdown-first to shutdown before erasing."
            return False, error or "Erase failed"

    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Erase an iOS simulator")
    parser.add_argument("--udid", required=True, help="Simulator UDID")
    parser.add_argument("--shutdown-first", action="store_true",
                        help="Shutdown the simulator before erasing")

    args = parser.parse_args()

    # Shutdown if requested
    if args.shutdown_first:
        shutdown_simulator(args.udid)

    success, message = erase_simulator(args.udid)

    if success:
        print(json.dumps({
            "success": True,
            "message": message,
            "udid": args.udid,
            "note": "All data and settings have been reset to factory defaults"
        }))
    else:
        print(json.dumps({
            "success": False,
            "error": message,
            "udid": args.udid
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
