---
name: record-sim-video
description: Record video from an iOS simulator screen. Useful for capturing app demos, bug reproductions, or UI test recordings.
---

# Record Simulator Video

Capture video from an iOS simulator.

## Usage

```bash
scripts/record-sim-video.py --udid SIMULATOR_UDID --output /path/to/video.mp4 [options]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--udid` | Yes | Simulator UDID |
| `--output` | Yes | Output video file path (.mp4 or .mov) |
| `--duration` | No | Recording duration in seconds |
| `--codec` | No | Video codec: h264 (default) or hevc |

## Examples

```bash
# Record until Ctrl+C is pressed
scripts/record-sim-video.py --udid XXXXXXXX --output /tmp/demo.mp4

# Record for 30 seconds
scripts/record-sim-video.py --udid XXXXXXXX --output /tmp/demo.mp4 --duration 30

# Record with HEVC codec (smaller file size)
scripts/record-sim-video.py --udid XXXXXXXX --output /tmp/demo.mp4 --codec hevc
```

## Output

```json
{
  "success": true,
  "message": "Recording completed",
  "output": "/tmp/demo.mp4",
  "size_bytes": 1234567,
  "codec": "h264"
}
```

## Notes

- Press Ctrl+C to stop recording (if no duration specified)
- The simulator must be booted
- Supports .mp4 and .mov output formats
- Uses the simulator's native screen recording capability
