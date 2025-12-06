#!/usr/bin/env python3
"""
List currently running Swift Package processes.

This script tracks processes started by swift-package-run.py with --background flag.
It reads from a tracking file stored in ~/.swift-package-processes.json

Usage:
    swift-package-list.py

Output:
    JSON with list of running processes (pid, executable name, package path, duration)
"""

import json
import sys
import os
import time


PROCESS_FILE = os.path.expanduser("~/.swift-package-processes.json")


def is_process_running(pid):
    """Check if a process with given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


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


def main():
    processes = load_processes()

    if not processes:
        print(json.dumps({
            "success": True,
            "message": "No running Swift Package processes",
            "count": 0,
            "processes": [],
            "hint": "Use swift-package-run.py --background to start a process"
        }))
        return

    # Filter out dead processes
    active_processes = []
    updated_processes = {}
    current_time = time.time()

    for pid_str, info in processes.items():
        pid = int(pid_str)
        if is_process_running(pid):
            duration = int(current_time - info.get("start_time", current_time))
            active_processes.append({
                "pid": pid,
                "executable": info.get("executable", "default"),
                "package_path": info.get("package_path", "unknown"),
                "duration_seconds": duration
            })
            updated_processes[pid_str] = info
        # Remove dead processes

    # Save cleaned up list
    save_processes(updated_processes)

    print(json.dumps({
        "success": True,
        "count": len(active_processes),
        "processes": active_processes,
        "hint": "Use swift-package-stop.py --pid <pid> to stop a process"
    }))


if __name__ == "__main__":
    main()
