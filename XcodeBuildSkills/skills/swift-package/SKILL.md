---
name: swift-package
description: Build, test, run, and manage Swift Package Manager projects. Use when working with Package.swift projects, running "swift build", "swift test", or "swift run", managing package executables, or cleaning SPM build artifacts.
---

# Swift Package

Manage Swift Package Manager projects with build, test, run, clean, and process management.

## Scripts

| Script | Purpose |
|--------|---------|
| `swift-package-build.py` | Build with `swift build` |
| `swift-package-test.py` | Run tests with `swift test` |
| `swift-package-run.py` | Run executables with `swift run` |
| `swift-package-clean.py` | Clean `.build` directory |
| `swift-package-list.py` | List running background processes |
| `swift-package-stop.py` | Stop a running process |

## Common Usage

```bash
# Build
scripts/swift-package-build.py --package-path <path> [--configuration release] [--target <name>]

# Test
scripts/swift-package-test.py --package-path <path> [--filter <pattern>] [--show-codecov]

# Run executable
scripts/swift-package-run.py --package-path <path> [--executable <name>] [--background]

# Clean
scripts/swift-package-clean.py --package-path <path>

# List/stop background processes
scripts/swift-package-list.py
scripts/swift-package-stop.py --pid <pid> [--force]
```

All scripts output JSON with `success`, `message`, and relevant details.
