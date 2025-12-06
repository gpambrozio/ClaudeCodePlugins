#!/usr/bin/env python3
"""
Xcode Doctor - Diagnose and validate Xcode development environment.

Usage:
    ./xcode-doctor.py [--verbose]

Options:
    --verbose    Show detailed output including all simulator runtimes
"""

import json
import subprocess
import sys
import os
import re


def run_command(cmd, capture_stderr=False):
    """Run a command and return output, or None if it fails."""
    try:
        stderr = subprocess.STDOUT if capture_stderr else subprocess.DEVNULL
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def get_xcode_info():
    """Get Xcode installation information."""
    info = {
        "installed": False,
        "path": None,
        "version": None,
        "build": None
    }

    # Get Xcode path
    path = run_command(["xcode-select", "-p"])
    if path:
        # Convert developer path to app path
        if "/Contents/Developer" in path:
            info["path"] = path.replace("/Contents/Developer", "")
        else:
            info["path"] = path
        info["installed"] = True

    # Get Xcode version
    version_output = run_command(["xcodebuild", "-version"])
    if version_output:
        lines = version_output.split("\n")
        for line in lines:
            if line.startswith("Xcode "):
                info["version"] = line.replace("Xcode ", "")
            elif line.startswith("Build version "):
                info["build"] = line.replace("Build version ", "")

    return info


def get_command_line_tools():
    """Check if command line tools are installed."""
    info = {
        "installed": False,
        "path": None
    }

    # Check for CLT
    clt_path = "/Library/Developer/CommandLineTools"
    if os.path.exists(clt_path):
        info["installed"] = True
        info["path"] = clt_path

    # Also check via xcode-select
    result = run_command(["xcode-select", "-p"])
    if result and "CommandLineTools" in result:
        info["installed"] = True
        info["path"] = result

    return info


def check_tool(tool_name, version_args=None):
    """Check if a tool is available and optionally get its version."""
    result = {
        "available": False,
        "version": None
    }

    # Check if tool exists
    which_result = run_command(["which", tool_name])
    if not which_result:
        # Try with xcrun
        which_result = run_command(["xcrun", "--find", tool_name])

    if which_result:
        result["available"] = True

        # Get version if args provided
        if version_args:
            version_output = run_command([tool_name] + version_args)
            if version_output:
                # Extract first line or version number
                result["version"] = version_output.split("\n")[0]

    return result


def get_simulators():
    """Get available simulator information."""
    info = {
        "available": False,
        "runtimes": [],
        "count": 0
    }

    # Get simulator list as JSON
    output = run_command(["xcrun", "simctl", "list", "--json"])
    if not output:
        return info

    try:
        data = json.loads(output)
        info["available"] = True

        # Get runtimes
        runtimes = data.get("runtimes", [])
        info["runtimes"] = [
            rt.get("name", rt.get("identifier", "Unknown"))
            for rt in runtimes
            if rt.get("isAvailable", True)
        ]

        # Count devices
        devices = data.get("devices", {})
        count = 0
        for runtime_devices in devices.values():
            count += len(runtime_devices)
        info["count"] = count

    except json.JSONDecodeError:
        pass

    return info


def get_devices():
    """Get connected physical devices."""
    info = {
        "available": False,
        "connected": 0,
        "list": []
    }

    # Try modern devicectl first (iOS 17+/Xcode 15+)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name

    try:
        result = subprocess.run(
            ["xcrun", "devicectl", "list", "devices", "--json-output", temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(temp_path):
            with open(temp_path, 'r') as f:
                data = json.load(f)

            devices = data.get("result", {}).get("devices", [])
            info["available"] = True
            info["connected"] = len(devices)
            info["list"] = [
                {
                    "name": d.get("deviceProperties", {}).get("name", "Unknown"),
                    "udid": d.get("hardwareProperties", {}).get("udid", "Unknown"),
                    "model": d.get("hardwareProperties", {}).get("marketingName", "Unknown")
                }
                for d in devices
            ]
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    # Fallback to xctrace if devicectl not available
    if not info["available"]:
        output = run_command(["xcrun", "xctrace", "list", "devices"])
        if output:
            info["available"] = True
            # Parse basic device info (format: Name (UUID))
            for line in output.split("\n"):
                if "(" in line and "Simulator" not in line:
                    match = re.match(r"(.+)\s+\(([A-F0-9-]+)\)", line.strip())
                    if match:
                        info["list"].append({
                            "name": match.group(1).strip(),
                            "udid": match.group(2)
                        })
            info["connected"] = len(info["list"])

    return info


def main():
    verbose = "--verbose" in sys.argv

    result = {
        "success": True,
        "xcode": get_xcode_info(),
        "command_line_tools": get_command_line_tools(),
        "tools": {
            "xcodebuild": check_tool("xcodebuild", ["-version"]),
            "xcrun": check_tool("xcrun", ["--version"]),
            "simctl": check_tool("simctl"),
            "devicectl": check_tool("devicectl")
        },
        "simulators": get_simulators(),
        "devices": get_devices()
    }

    # Determine overall success
    if not result["xcode"]["installed"]:
        result["success"] = False
        result["error"] = "Xcode is not installed"
    elif not result["tools"]["xcodebuild"]["available"]:
        result["success"] = False
        result["error"] = "xcodebuild is not available"

    # Limit runtimes in non-verbose mode
    if not verbose and len(result["simulators"]["runtimes"]) > 5:
        result["simulators"]["runtimes"] = result["simulators"]["runtimes"][:5]
        result["simulators"]["runtimes_truncated"] = True

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
