---
name: swift-package-list
description: List currently running Swift Package processes that were started with swift-package-run. Use to check the status of background Swift package executables.
---

# Swift Package List

List running Swift package processes.

## Usage

```bash
scripts/swift-package-list.py
```

## Arguments

This script takes no arguments.

## Output

```json
{
  "success": true,
  "count": 2,
  "processes": [
    {
      "pid": 12345,
      "executable": "mytool",
      "package_path": "/path/to/MyPackage",
      "duration_seconds": 120
    }
  ],
  "hint": "Use swift-package-stop.py --pid <pid> to stop a process"
}
```

## Notes

- Only tracks processes started with `swift-package-run.py --background`
- Automatically cleans up entries for processes that are no longer running
- Process information is stored in `~/.swift-package-processes.json`
