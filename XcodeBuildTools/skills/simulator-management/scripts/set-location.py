#!/usr/bin/env python3
"""
Set simulated GPS location on an iOS Simulator.

Usage:
    ./set-location.py --udid <UDID> --latitude 37.7749 --longitude -122.4194
    ./set-location.py --udid <UDID> --location "San Francisco"

Options:
    --udid UDID            Simulator UDID
    --latitude LAT         Latitude (-90 to 90)
    --longitude LON        Longitude (-180 to 180)
    --location NAME        Named location (San Francisco, New York, London, Tokyo)
"""

import argparse
import json
import subprocess
import sys


# Named locations
LOCATIONS = {
    "san francisco": (37.7749, -122.4194),
    "sf": (37.7749, -122.4194),
    "new york": (40.7128, -74.0060),
    "nyc": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
    "paris": (48.8566, 2.3522),
    "sydney": (-33.8688, 151.2093),
    "los angeles": (34.0522, -118.2437),
    "la": (34.0522, -118.2437),
    "seattle": (47.6062, -122.3321),
    "austin": (30.2672, -97.7431),
    "cupertino": (37.3230, -122.0322),
}


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
            return None

        data = json.loads(result.stdout)

        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("state") == "Booted":
                    return device.get("udid")

        return None

    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Set simulator GPS location")
    parser.add_argument("--udid", help="Simulator UDID")
    parser.add_argument("--latitude", type=float, help="Latitude (-90 to 90)")
    parser.add_argument("--longitude", type=float, help="Longitude (-180 to 180)")
    parser.add_argument("--location", help="Named location")

    args = parser.parse_args()

    # Get simulator UDID
    simulator_udid = args.udid
    if not simulator_udid:
        simulator_udid = get_booted_simulator()
        if not simulator_udid:
            print(json.dumps({
                "success": False,
                "error": "No booted simulator found. Specify --udid or boot a simulator first."
            }))
            return 1

    # Get coordinates
    latitude = args.latitude
    longitude = args.longitude

    if args.location:
        location_key = args.location.lower()
        if location_key not in LOCATIONS:
            print(json.dumps({
                "success": False,
                "error": f"Unknown location '{args.location}'. Available: {', '.join(LOCATIONS.keys())}"
            }))
            return 1
        latitude, longitude = LOCATIONS[location_key]

    if latitude is None or longitude is None:
        print(json.dumps({
            "success": False,
            "error": "Either --latitude/--longitude or --location is required"
        }))
        return 1

    # Validate coordinates
    if latitude < -90 or latitude > 90:
        print(json.dumps({
            "success": False,
            "error": "Latitude must be between -90 and 90"
        }))
        return 1

    if longitude < -180 or longitude > 180:
        print(json.dumps({
            "success": False,
            "error": "Longitude must be between -180 and 180"
        }))
        return 1

    try:
        result = subprocess.run(
            ["xcrun", "simctl", "location", simulator_udid, "set", f"{latitude},{longitude}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            response = {
                "success": True,
                "message": "Location set",
                "latitude": latitude,
                "longitude": longitude,
                "udid": simulator_udid
            }
            if args.location:
                response["location_name"] = args.location

            print(json.dumps(response, indent=2))
            return 0
        else:
            print(json.dumps({
                "success": False,
                "error": result.stderr or "Failed to set location"
            }))
            return 1

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
