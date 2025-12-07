---
name: swift-package
description: Build, test, run, and manage Swift Package Manager projects. Use when working with Package.swift projects, running "swift build", "swift test", or "swift run", managing package executables, or cleaning SPM build artifacts.
---

# Swift Package

Manage Swift Package Manager projects.

## Prerequisites

For build/test output parsing: `brew install xcsift`

## Build & Test (with xcsift)

```bash
cd /path/to/package

# Build
swift build 2>&1 | tee /tmp/build.log | xcsift --warnings

# Build release
swift build -c release 2>&1 | tee /tmp/build.log | xcsift --warnings

# Test
swift test 2>&1 | tee /tmp/test.log | xcsift --warnings

# Test with filter
swift test --filter "testLogin" 2>&1 | tee /tmp/test.log | xcsift --warnings
```

## Run & Process Management

```bash
# Run default executable
scripts/swift-package-run.py --package-path <path> [--executable <name>] [--background]

# List running background processes
scripts/swift-package-list.py

# Stop a process
scripts/swift-package-stop.py --pid <pid> [--force]
```

## Clean

```bash
# Clean build artifacts
swift package clean

# Or remove .build directory directly
rm -rf /path/to/package/.build
```

Output from `xcsift`: JSON with `success`, `errors`, `warnings`. Check log files for full output.
