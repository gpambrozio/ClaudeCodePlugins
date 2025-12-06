#!/usr/bin/env python3
"""
Build and run a Swift package executable.

Usage:
    ./swift-run.py --path /path/to/package
    ./swift-run.py --path /path/to/package --target MyCLI
    ./swift-run.py --path /path/to/package --target MyCLI -- --verbose input.txt

Options:
    --path PATH       Path to Swift package
    --target TARGET   Executable target to run
    -- ARGS           Arguments to pass to executable
"""

import argparse
import json
import subprocess
import sys
import os


def main():
    # Find the separator
    separator_idx = None
    for i, arg in enumerate(sys.argv):
        if arg == "--":
            separator_idx = i
            break

    if separator_idx:
        our_args = sys.argv[1:separator_idx]
        exec_args = sys.argv[separator_idx + 1:]
    else:
        our_args = sys.argv[1:]
        exec_args = []

    parser = argparse.ArgumentParser(description="Run Swift package executable")
    parser.add_argument("--path", default=".", help="Path to Swift package")
    parser.add_argument("--target", help="Executable target to run")
    parser.add_argument("--configuration", choices=["debug", "release"], default="debug", help="Build configuration")

    args = parser.parse_args(our_args)

    # Resolve and validate path
    package_path = os.path.abspath(args.path)
    package_swift = os.path.join(package_path, "Package.swift")

    if not os.path.exists(package_swift):
        print(json.dumps({
            "success": False,
            "error": f"No Package.swift found at {package_path}"
        }))
        return 1

    # Build command
    cmd = ["swift", "run", "--package-path", package_path]

    if args.configuration == "release":
        cmd.extend(["-c", "release"])

    if args.target:
        cmd.append(args.target)

    if exec_args:
        cmd.extend(exec_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print(json.dumps({
                "success": True,
                "message": "Execution completed",
                "target": args.target,
                "output": result.stdout[:5000] if result.stdout else None,
                "output_truncated": len(result.stdout) > 5000 if result.stdout else False
            }, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": "Execution failed",
                "stderr": result.stderr[:2000] if result.stderr else None,
                "return_code": result.returncode
            }, indent=2))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Execution timed out after 5 minutes"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
