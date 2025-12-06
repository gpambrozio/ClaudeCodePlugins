---
name: start-sim-log
description: Start capturing logs from an iOS simulator app. Streams structured logs from a specific app bundle. Use for debugging and monitoring app behavior.
---

# Start Simulator Log Capture

Stream logs from an app running in the iOS Simulator.

## Usage

```bash
scripts/start-sim-log.py --udid SIMULATOR_UDID --bundle-id com.example.MyApp [options]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--udid` | Yes | Simulator UDID |
| `--bundle-id` | Yes | Bundle identifier of the app |
| `--output` | No | File path to write logs (default: stdout) |
| `--level` | No | Log level: default, info, debug |

## Examples

```bash
# Stream logs to terminal
scripts/start-sim-log.py --udid XXXXXXXX --bundle-id com.example.MyApp

# Save logs to file
scripts/start-sim-log.py --udid XXXXXXXX --bundle-id com.example.MyApp --output /tmp/app.log

# Include debug-level logs
scripts/start-sim-log.py --udid XXXXXXXX --bundle-id com.example.MyApp --level debug
```

## Notes

- Press Ctrl+C to stop capture
- Logs are filtered by the app's bundle identifier
- Uses `xcrun simctl spawn` with the unified logging system
- The simulator must be booted and the app should be running

## Log Levels

| Level | Description |
|-------|-------------|
| `default` | Standard log messages |
| `info` | Informational messages (more verbose) |
| `debug` | Debug messages (most verbose) |
