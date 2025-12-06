#!/usr/bin/env python3
"""
Stop a running Swift Package executable started with swift-package-run.

Usage:
    swift-package-stop.py --pid PID

Arguments:
    --pid PID    Process ID of the running executable (required)
    --force      Force kill with SIGKILL instead of SIGTERM

Output:
    JSON with success status and message
"""

import argparse
import json
import sys
import os
import signal
import time


PROCESS_FILE = os.path.expanduser("~/.swift-package-processes.json")


def load_processes():
    """Load tracked processes from file."""
    if not os.path.exists(PROCESS_FILE):
        return {}
    try:
        with open(PROCESS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_processes(processes):
    """Save tracked processes to file."""
    try:
        with open(PROCESS_FILE, 'w') as f:
            json.dump(processes, f)
    except IOError:
        pass


def is_process_running(pid):
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description="Stop a running Swift Package executable")
    parser.add_argument("--pid", type=int, required=True, help="Process ID to stop")
    parser.add_argument("--force", action="store_true", help="Force kill with SIGKILL")

    args = parser.parse_args()
    pid = args.pid

    # Check if process exists
    if not is_process_running(pid):
        # Remove from tracking if it exists
        processes = load_processes()
        if str(pid) in processes:
            del processes[str(pid)]
            save_processes(processes)

        print(json.dumps({
            "success": True,
            "message": f"Process {pid} is not running (may have already exited)",
            "pid": pid
        }))
        return

    try:
        # Try graceful shutdown first
        if args.force:
            os.kill(pid, signal.SIGKILL)
            terminated = True
        else:
            os.kill(pid, signal.SIGTERM)

            # Wait for process to terminate (with timeout)
            timeout = 5  # seconds
            start = time.time()
            terminated = False

            while time.time() - start < timeout:
                if not is_process_running(pid):
                    terminated = True
                    break
                time.sleep(0.1)

            # Force kill if still running
            if not terminated and is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
                terminated = not is_process_running(pid)

        # Remove from tracking
        processes = load_processes()
        process_info = processes.pop(str(pid), {})
        save_processes(processes)

        if terminated:
            print(json.dumps({
                "success": True,
                "message": f"Process {pid} stopped successfully",
                "pid": pid,
                "executable": process_info.get("executable", "unknown"),
                "package_path": process_info.get("package_path", "unknown")
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": f"Failed to stop process {pid}",
                "pid": pid,
                "hint": "Try using --force flag"
            }))
            sys.exit(1)

    except PermissionError:
        print(json.dumps({
            "success": False,
            "error": f"Permission denied to stop process {pid}",
            "pid": pid
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "pid": pid
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
