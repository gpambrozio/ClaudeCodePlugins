---
name: sim-log
description: Capture logs from iOS Simulator apps. Use when debugging simulator apps, monitoring app output, or capturing logs for analysis.
---

# Simulator Log Capture

Stream logs from apps running in iOS Simulator.

## Start Capture

```bash
scripts/start-sim-log.py --udid <sim-udid> --bundle-id <id> \
  [--output <file>] [--level default|info|debug]
```

Runs continuously until Ctrl+C or process kill.

## Stop Capture

Press **Ctrl+C** in terminal, or:
```bash
pkill -f "simctl spawn.*log stream"
```

The simulator must be booted and app should be running.
