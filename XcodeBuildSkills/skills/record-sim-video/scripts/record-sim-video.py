#!/usr/bin/env python3
"""
Record video from an iOS simulator.

Usage:
    record-sim-video.py --udid SIMULATOR_UDID --output /path/to/video.mp4 --duration SECONDS
    record-sim-video.py --udid SIMULATOR_UDID --output /path/to/video.mp4 --stop

Arguments:
    --udid UDID           Simulator UDID
    --output PATH         Output video file path (.mp4 or .mov)
    --duration SECONDS    Record for specified duration (optional, records until Ctrl+C if not set)
    --codec CODEC         Video codec: h264 (default) or hevc

Output:
    JSON with recording status and file path
"""

import argparse
import json
import subprocess
import sys
import os
import signal
import time
import threading


def main():
    parser = argparse.ArgumentParser(description="Record video from iOS simulator")
    parser.add_argument("--udid", required=True, help="Simulator UDID")
    parser.add_argument("--output", required=True, help="Output video file path")
    parser.add_argument("--duration", type=int, help="Recording duration in seconds")
    parser.add_argument("--codec", choices=["h264", "hevc"], default="h264",
                        help="Video codec")

    args = parser.parse_args()

    output_path = os.path.abspath(args.output)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "xcrun", "simctl", "io", args.udid, "recordVideo",
        "--codec", args.codec,
        output_path
    ]

    process = None

    def stop_recording(signum=None, frame=None):
        if process:
            process.terminate()

    try:
        # Start recording
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Print start message
        sys.stderr.write(json.dumps({
            "success": True,
            "message": "Recording started",
            "simulator": args.udid,
            "output": output_path,
            "hint": "Press Ctrl+C to stop recording" if not args.duration else f"Recording for {args.duration} seconds..."
        }) + "\n")
        sys.stderr.flush()

        # Set up signal handler for graceful stop
        signal.signal(signal.SIGINT, stop_recording)
        signal.signal(signal.SIGTERM, stop_recording)

        if args.duration:
            # Wait for specified duration
            time.sleep(args.duration)
            process.terminate()
        else:
            # Wait for process or Ctrl+C
            process.wait()

        # Wait for process to finish
        process.wait(timeout=10)

        # Check if file was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(json.dumps({
                "success": True,
                "message": "Recording completed",
                "output": output_path,
                "size_bytes": file_size,
                "codec": args.codec
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": "Video file was not created",
                "output": output_path
            }))
            sys.exit(1)

    except KeyboardInterrupt:
        if process:
            process.terminate()
            process.wait(timeout=10)

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(json.dumps({
                "success": True,
                "message": "Recording stopped",
                "output": output_path,
                "size_bytes": file_size
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": "Recording was interrupted before video was saved"
            }))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
