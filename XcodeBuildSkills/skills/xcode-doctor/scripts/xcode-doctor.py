#!/usr/bin/env python3
"""
Diagnose Xcode development environment and check tool availability.

Usage:
    xcode-doctor.py

Checks:
    - Xcode installation and version
    - Command Line Tools
    - Available simulators
    - Connected devices
    - Swift version
    - Active developer directory

Output:
    JSON with diagnostic results
"""

import json
import subprocess
import sys
import os
import platform


def run_command(cmd, timeout=30):
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, "Command not found"
    except Exception as e:
        return False, str(e)


def get_xcode_version():
    """Get Xcode version."""
    success, output = run_command(["xcodebuild", "-version"])
    if success:
        lines = output.split('\n')
        version = lines[0].replace("Xcode ", "") if lines else "Unknown"
        build = lines[1].replace("Build version ", "") if len(lines) > 1 else "Unknown"
        return {"installed": True, "version": version, "build": build}
    return {"installed": False, "error": output}


def get_developer_dir():
    """Get active developer directory."""
    success, output = run_command(["xcode-select", "-p"])
    return {"path": output if success else None, "valid": success}


def get_swift_version():
    """Get Swift version."""
    success, output = run_command(["swift", "--version"])
    if success:
        # Parse version from output like "Swift version 5.9 (swiftlang-...)"
        for part in output.split():
            if part[0].isdigit():
                return {"version": part, "installed": True}
        return {"version": output.split('\n')[0], "installed": True}
    return {"installed": False, "error": output}


def get_simulator_count():
    """Count available simulators."""
    success, output = run_command(["xcrun", "simctl", "list", "devices", "-j"])
    if success:
        try:
            data = json.loads(output)
            devices = data.get("devices", {})
            total = sum(len(v) for v in devices.values())
            booted = sum(1 for devs in devices.values() for d in devs if d.get("state") == "Booted")
            return {"total": total, "booted": booted, "available": True}
        except json.JSONDecodeError:
            return {"available": False, "error": "Failed to parse simulator list"}
    return {"available": False, "error": output}


def get_device_count():
    """Count connected physical devices."""
    success, output = run_command(["xcrun", "xctrace", "list", "devices"])
    if success:
        # Count lines in the Devices section
        in_devices = False
        count = 0
        for line in output.split('\n'):
            if '== Devices ==' in line:
                in_devices = True
                continue
            if '== Simulators ==' in line:
                break
            if in_devices and line.strip():
                count += 1
        return {"connected": count, "available": True}
    return {"available": False, "error": output}


def check_command_available(cmd):
    """Check if a command is available."""
    success, _ = run_command(["which", cmd])
    return success


def main():
    diagnostics = {
        "success": True,
        "system": {
            "os": platform.system(),
            "os_version": platform.mac_ver()[0],
            "architecture": platform.machine()
        },
        "xcode": get_xcode_version(),
        "developer_dir": get_developer_dir(),
        "swift": get_swift_version(),
        "simulators": get_simulator_count(),
        "devices": get_device_count(),
        "tools": {
            "xcodebuild": check_command_available("xcodebuild"),
            "xcrun": check_command_available("xcrun"),
            "simctl": check_command_available("xcrun"),
            "swift": check_command_available("swift"),
            "git": check_command_available("git"),
            "pod": check_command_available("pod"),
            "carthage": check_command_available("carthage")
        }
    }

    # Determine overall health
    issues = []

    if not diagnostics["xcode"].get("installed"):
        issues.append("Xcode is not installed or not configured")

    if not diagnostics["developer_dir"].get("valid"):
        issues.append("Developer directory is not set (run: xcode-select --install)")

    if not diagnostics["swift"].get("installed"):
        issues.append("Swift is not available")

    if not diagnostics["tools"]["xcodebuild"]:
        issues.append("xcodebuild is not available")

    if issues:
        diagnostics["health"] = "issues"
        diagnostics["issues"] = issues
    else:
        diagnostics["health"] = "good"
        diagnostics["message"] = "Development environment is properly configured"

    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
