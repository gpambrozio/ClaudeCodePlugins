---
name: stop-sim-log
description: Instructions for stopping simulator log capture. Since start-sim-log streams continuously, use Ctrl+C or kill the process to stop.
---

# Stop Simulator Log Capture

Stop an active log capture session.

## How to Stop

Log capture started with `start-sim-log.py` runs continuously until stopped.

### Interactive Mode
If running in a terminal, press **Ctrl+C** to stop the capture.

### Background Process
If the log capture was started in the background, find and kill the process:

```bash
# Find the log process
ps aux | grep "simctl.*log stream"

# Kill by PID
kill <PID>

# Or kill all log stream processes for a simulator
pkill -f "simctl spawn.*log stream"
```

## Notes

- Stopping the capture is graceful - any buffered logs will be flushed
- If writing to a file, the file will be properly closed
- The app continues running after log capture stops
