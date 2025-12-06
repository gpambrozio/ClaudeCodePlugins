#!/usr/bin/env python3
"""
List connected physical Apple devices (iPhone, iPad, Apple Watch, Apple TV, Vision Pro).

Usage:
    list-devices.py

This script uses Xcode's devicectl (Xcode 15+) or falls back to xctrace for older versions.

Output:
    JSON with list of connected devices including UDID, name, platform, and connection status
"""

import json
import subprocess
import sys
import re


def list_devices_devicectl():
    """List devices using devicectl (Xcode 15+)."""
    try:
        # Use /dev/stdout to capture JSON output directly without temp files
        result = subprocess.run(
            ["xcrun", "devicectl", "list", "devices", "--json-output", "/dev/stdout"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, "devicectl failed"

        # Parse JSON from stdout
        data = json.loads(result.stdout)

        devices = []
        device_list = data.get("result", {}).get("devices", [])

        for device in device_list:
            # Skip simulators
            if device.get("deviceProperties", {}).get("bootedFromSnapshot"):
                continue

            device_info = {
                "udid": device.get("identifier"),
                "name": device.get("deviceProperties", {}).get("name"),
                "platform": device.get("deviceProperties", {}).get("platform", "Unknown"),
                "os_version": device.get("deviceProperties", {}).get("osVersionNumber"),
                "model": device.get("hardwareProperties", {}).get("marketingName"),
                "architecture": device.get("hardwareProperties", {}).get("cpuType", {}).get("name"),
                "connected": device.get("connectionProperties", {}).get("tunnelState") == "connected",
                "paired": device.get("connectionProperties", {}).get("pairingState") == "paired",
                "developer_mode": device.get("deviceProperties", {}).get("developerModeStatus") == "enabled"
            }

            # Only include actual devices (have UDID)
            if device_info["udid"]:
                devices.append(device_info)

        return devices, None

    except subprocess.TimeoutExpired:
        return None, "Command timed out"
    except json.JSONDecodeError:
        return None, "Failed to parse devicectl output"
    except Exception as e:
        return None, str(e)


def list_devices_xctrace():
    """Fallback: list devices using xctrace."""
    try:
        result = subprocess.run(
            ["xcrun", "xctrace", "list", "devices"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, "xctrace failed"

        devices = []
        in_devices = False

        for line in result.stdout.split('\n'):
            line = line.strip()

            if '== Devices ==' in line:
                in_devices = True
                continue

            if '== Simulators ==' in line:
                break

            if in_devices and line:
                # Parse line format: "Device Name (OS Version) (UDID)"
                match = re.match(r'^(.+?)\s+\(([^)]+)\)\s+\(([A-Fa-f0-9-]+)\)$', line)
                if match:
                    devices.append({
                        "name": match.group(1).strip(),
                        "os_version": match.group(2),
                        "udid": match.group(3)
                    })

        return devices, None

    except Exception as e:
        return None, str(e)


def main():
    # Try devicectl first (Xcode 15+)
    devices, error = list_devices_devicectl()

    if devices is None:
        # Fallback to xctrace
        devices, error = list_devices_xctrace()

    if devices is None:
        print(json.dumps({
            "success": False,
            "error": error or "Failed to list devices",
            "hint": "Make sure a device is connected and you have accepted the trust dialog"
        }))
        sys.exit(1)

    if not devices:
        print(json.dumps({
            "success": True,
            "message": "No physical devices connected",
            "count": 0,
            "devices": [],
            "hints": [
                "Connect an iPhone, iPad, or other Apple device via USB or Wi-Fi",
                "Trust the computer on the device when prompted",
                "Enable Developer Mode on iOS 16+ devices (Settings > Privacy & Security > Developer Mode)"
            ]
        }))
        return

    # Group by connection status
    connected = [d for d in devices if d.get("connected", True)]
    disconnected = [d for d in devices if not d.get("connected", True)]

    print(json.dumps({
        "success": True,
        "count": len(devices),
        "connected_count": len(connected),
        "devices": devices,
        "message": f"Found {len(devices)} device(s), {len(connected)} connected"
    }))


if __name__ == "__main__":
    main()
