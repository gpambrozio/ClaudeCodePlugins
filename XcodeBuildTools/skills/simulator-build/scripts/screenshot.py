#!/usr/bin/env python3
"""
Take a screenshot of an iOS Simulator.

Usage:
    ./screenshot.py [--simulator-id <UDID>] [--output /path/to/screenshot.png]

Options:
    --simulator-id UDID    Simulator UDID (uses booted if not specified)
    --output PATH          Output file path (auto-generated if not specified)
"""

import argparse
import json
import subprocess
import sys
import os
import time


def get_booted_simulator():
    """Get the first booted simulator."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, "Failed to list simulators"

        data = json.loads(result.stdout)

        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("state") == "Booted":
                    return device.get("udid"), None

        return None, "No booted simulator found. Boot a simulator first."

    except Exception as e:
        return None, str(e)


def get_simulator_info(simulator_id):
    """Get simulator screen info."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("udid") == simulator_id:
                    return device.get("name", "Unknown")

        return None

    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Take simulator screenshot")
    parser.add_argument("--simulator-id", help="Simulator UDID")
    parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    # Get simulator ID
    simulator_id = args.simulator_id
    if not simulator_id:
        simulator_id, error = get_booted_simulator()
        if error:
            print(json.dumps({"success": False, "error": error}))
            return 1

    # Generate output path if not provided
    output_path = args.output
    if not output_path:
        timestamp = int(time.time())
        output_path = f"/tmp/sim-screenshot-{timestamp}.png"

    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        result = subprocess.run(
            ["xcrun", "simctl", "io", simulator_id, "screenshot", output_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(output_path):
            # Get file size
            size_bytes = os.path.getsize(output_path)

            # Try to get image dimensions
            screen_info = {}
            try:
                from PIL import Image
                with Image.open(output_path) as img:
                    width, height = img.size
                    # Estimate scale (common scales are 2 or 3 for Retina)
                    scale = 3 if width > 1000 else 2
                    screen_info = {
                        "width_pixels": width,
                        "height_pixels": height,
                        "width_points": width // scale,
                        "height_points": height // scale,
                        "scale": scale
                    }
            except ImportError:
                pass  # PIL not available

            response = {
                "success": True,
                "message": "Screenshot saved",
                "path": output_path,
                "simulator_id": simulator_id,
                "size_bytes": size_bytes
            }

            if screen_info:
                response["screen"] = screen_info

            # Get simulator name
            name = get_simulator_info(simulator_id)
            if name:
                response["simulator_name"] = name

            print(json.dumps(response, indent=2))
            return 0
        else:
            error = result.stderr or result.stdout or "Screenshot failed"
            print(json.dumps({"success": False, "error": error}))
            return 1

    except subprocess.TimeoutExpired:
        print(json.dumps({"success": False, "error": "Screenshot timed out"}))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
