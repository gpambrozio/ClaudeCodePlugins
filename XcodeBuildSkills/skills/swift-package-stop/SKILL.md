---
name: swift-package-stop
description: Stop a running Swift Package executable that was started with swift-package-run. Sends SIGTERM for graceful shutdown, or SIGKILL with --force flag.
---

# Swift Package Stop

Stop a running Swift package process.

## Usage

```bash
scripts/swift-package-stop.py --pid PID [--force]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--pid` | Yes | Process ID of the running executable |
| `--force` | No | Force kill with SIGKILL instead of SIGTERM |

## Examples

```bash
# Graceful shutdown
scripts/swift-package-stop.py --pid 12345

# Force kill
scripts/swift-package-stop.py --pid 12345 --force
```

## Output

```json
{
  "success": true,
  "message": "Process 12345 stopped successfully",
  "pid": 12345,
  "executable": "mytool",
  "package_path": "/path/to/MyPackage"
}
```

## Notes

- First attempts graceful shutdown with SIGTERM
- Waits up to 5 seconds for graceful exit
- Falls back to SIGKILL if process doesn't terminate
- Use `--force` to skip graceful shutdown and immediately SIGKILL
