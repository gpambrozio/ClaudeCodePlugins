#!/usr/bin/env python3
"""
Record video of an iOS Simulator.

Usage:
    ./record-video.py --simulator-id <UDID> --output /path/to/video.mp4 --start
    ./record-video.py --stop

Options:
    --simulator-id UDID    Simulator UDID
    --output PATH          Output file path
    --start                Start recording
    --stop                 Stop recording
    --codec CODEC          Video codec (h264, hevc) - default: h264
"""

import argparse
import json
import subprocess
import sys
import os
import signal
import time

PID_FILE = "/tmp/simctl-record.pid"


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

        return None, "No booted simulator found"

    except Exception as e:
        return None, str(e)


def start_recording(simulator_id, output_path, codec="h264"):
    """Start video recording."""
    # Check if already recording
    if os.path.exists(PID_FILE):
        print(json.dumps({
            "success": False,
            "error": "Recording already in progress. Use --stop first."
        }))
        return 1

    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # Start recording in background
        cmd = ["xcrun", "simctl", "io", simulator_id, "recordVideo"]

        if codec:
            cmd.extend(["--codec", codec])

        cmd.append(output_path)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Save PID and output path for later
        with open(PID_FILE, "w") as f:
            f.write(f"{process.pid}\n{output_path}\n{simulator_id}")

        print(json.dumps({
            "success": True,
            "message": "Recording started",
            "output": output_path,
            "simulator_id": simulator_id,
            "pid": process.pid,
            "hint": "Use --stop to stop recording"
        }, indent=2))
        return 0

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


def stop_recording():
    """Stop video recording."""
    if not os.path.exists(PID_FILE):
        print(json.dumps({
            "success": False,
            "error": "No recording in progress"
        }))
        return 1

    try:
        with open(PID_FILE, "r") as f:
            lines = f.read().strip().split("\n")
            pid = int(lines[0])
            output_path = lines[1] if len(lines) > 1 else None
            simulator_id = lines[2] if len(lines) > 2 else None

        # Send SIGINT to gracefully stop recording
        os.kill(pid, signal.SIGINT)

        # Wait a bit for file to be finalized
        time.sleep(1)

        # Clean up PID file
        os.unlink(PID_FILE)

        response = {
            "success": True,
            "message": "Recording stopped"
        }

        if output_path:
            response["output"] = output_path
            if os.path.exists(output_path):
                response["size_bytes"] = os.path.getsize(output_path)

        if simulator_id:
            response["simulator_id"] = simulator_id

        print(json.dumps(response, indent=2))
        return 0

    except ProcessLookupError:
        # Process already stopped
        if os.path.exists(PID_FILE):
            os.unlink(PID_FILE)
        print(json.dumps({
            "success": True,
            "message": "Recording process was already stopped"
        }))
        return 0
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


def main():
    parser = argparse.ArgumentParser(description="Record simulator video")
    parser.add_argument("--simulator-id", help="Simulator UDID")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--start", action="store_true", help="Start recording")
    parser.add_argument("--stop", action="store_true", help="Stop recording")
    parser.add_argument("--codec", default="h264", choices=["h264", "hevc"], help="Video codec")

    args = parser.parse_args()

    if args.stop:
        return stop_recording()

    if args.start:
        # Get simulator ID
        simulator_id = args.simulator_id
        if not simulator_id:
            simulator_id, error = get_booted_simulator()
            if error:
                print(json.dumps({"success": False, "error": error}))
                return 1

        # Get output path
        output_path = args.output
        if not output_path:
            timestamp = int(time.time())
            output_path = f"/tmp/sim-recording-{timestamp}.mp4"

        return start_recording(simulator_id, output_path, args.codec)

    print(json.dumps({
        "success": False,
        "error": "Specify --start or --stop"
    }))
    return 1


if __name__ == "__main__":
    sys.exit(main())
