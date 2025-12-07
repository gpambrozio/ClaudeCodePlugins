#!/usr/bin/env python3
"""
Run an executable target from a Swift Package using `swift run`.

Usage:
    swift-package-run.py --package-path /path/to/package [options]

Arguments:
    --package-path PATH    Path to the Swift package root (required)
    --executable NAME      Name of executable to run (defaults to package name)
    --configuration CFG    Build configuration: debug (default) or release
    --arguments ARGS       Arguments to pass to the executable
    --timeout SECONDS      Timeout in seconds (default: 30, max: 300)
    --background           Run in background and return immediately
    --parse-as-library     Add -parse-as-library flag for @main support

Output:
    JSON with success status, output or process ID (for background)
"""

import argparse
import json
import subprocess
import sys
import os
import signal
import time


def main():
    parser = argparse.ArgumentParser(description="Run Swift Package executable")
    parser.add_argument("--package-path", required=True, help="Path to Swift package root")
    parser.add_argument("--executable", help="Name of executable to run")
    parser.add_argument("--configuration", choices=["debug", "release"], default="debug")
    parser.add_argument("--arguments", nargs="*", default=[], help="Arguments to pass to the executable")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds (max 300)")
    parser.add_argument("--background", action="store_true", help="Run in background")
    parser.add_argument("--parse-as-library", action="store_true", help="Add -parse-as-library flag")

    args = parser.parse_args()

    # Resolve to absolute path
    package_path = os.path.abspath(args.package_path)

    if not os.path.isdir(package_path):
        print(json.dumps({
            "success": False,
            "error": f"Package path does not exist: {package_path}"
        }))
        sys.exit(1)

    # Enforce max timeout
    timeout = min(args.timeout, 300)

    # Build command
    cmd = ["swift", "run", "--package-path", package_path]

    if args.configuration == "release":
        cmd.extend(["-c", "release"])

    if args.parse_as_library:
        cmd.extend(["-Xswiftc", "-parse-as-library"])

    if args.executable:
        cmd.append(args.executable)

    if args.arguments:
        cmd.append("--")
        cmd.extend(args.arguments)

    try:
        if args.background:
            # Run in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=package_path,
                start_new_session=True
            )
            print(json.dumps({
                "success": True,
                "message": "Process started in background",
                "pid": process.pid,
                "package_path": package_path,
                "executable": args.executable or "default",
                "hint": "Use swift-package-stop.py --pid <pid> to stop the process"
            }))
        else:
            # Run with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=package_path,
                timeout=timeout
            )

            if result.returncode == 0:
                print(json.dumps({
                    "success": True,
                    "message": "Execution completed",
                    "package_path": package_path,
                    "output": result.stdout.strip() if result.stdout.strip() else "Completed with no output"
                }))
            else:
                print(json.dumps({
                    "success": False,
                    "error": "Execution failed",
                    "stderr": result.stderr.strip(),
                    "stdout": result.stdout.strip(),
                    "return_code": result.returncode
                }))
                sys.exit(1)

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "success": False,
            "error": f"Execution timed out after {timeout} seconds",
            "hint": "Use --background flag for long-running processes or increase --timeout"
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
