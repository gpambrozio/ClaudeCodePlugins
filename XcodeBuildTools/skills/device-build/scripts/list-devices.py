#!/usr/bin/env python3
"""
List connected physical Apple devices.

Usage:
    ./list-devices.py [--json-pretty]

Output: JSON with device list
"""

import json
import subprocess
import sys
import os
import tempfile
import re


def run_command(cmd, timeout=30):
    """Run a command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def list_devices_devicectl():
    """List devices using devicectl (Xcode 15+/iOS 17+)."""
    devices = []

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name

    try:
        success, stdout, stderr = run_command([
            "xcrun", "devicectl", "list", "devices", "--json-output", temp_path
        ])

        if success and os.path.exists(temp_path):
            with open(temp_path, 'r') as f:
                data = json.load(f)

            for device in data.get("result", {}).get("devices", []):
                hw = device.get("hardwareProperties", {})
                dp = device.get("deviceProperties", {})
                conn = device.get("connectionProperties", {})

                # Skip simulators
                if hw.get("deviceType") == "simulator":
                    continue

                devices.append({
                    "name": dp.get("name", "Unknown"),
                    "udid": hw.get("udid", "Unknown"),
                    "model": hw.get("marketingName", hw.get("productType", "Unknown")),
                    "os_version": dp.get("osVersionNumber", "Unknown"),
                    "connection": conn.get("transportType", "Unknown"),
                    "paired": conn.get("pairingState") == "paired"
                })

            return devices, None

    except Exception as e:
        return None, str(e)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return None, "devicectl failed"


def list_devices_xctrace():
    """Fallback: List devices using xctrace."""
    devices = []

    success, stdout, stderr = run_command(["xcrun", "xctrace", "list", "devices"])
    if not success:
        return None, stderr

    # Parse output - format: "Device Name (UDID)"
    for line in stdout.split("\n"):
        line = line.strip()
        if not line or "Simulator" in line or "==" in line:
            continue

        # Match pattern: Name (UUID)
        match = re.match(r"^(.+?)\s+\(([A-Fa-f0-9-]+)\)$", line)
        if match:
            devices.append({
                "name": match.group(1).strip(),
                "udid": match.group(2),
                "model": "Unknown",
                "os_version": "Unknown",
                "connection": "Unknown",
                "paired": True
            })

    return devices, None


def main():
    # Try devicectl first (modern method)
    devices, error = list_devices_devicectl()

    # Fallback to xctrace
    if devices is None:
        devices, error = list_devices_xctrace()

    if devices is None:
        result = {
            "success": False,
            "error": error or "Failed to list devices",
            "devices": []
        }
    else:
        result = {
            "success": True,
            "count": len(devices),
            "devices": devices
        }
        if len(devices) == 0:
            result["message"] = "No physical devices connected. Connect a device via USB or ensure it's paired over network."

    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
