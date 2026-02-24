---
name: swift-package
description: Build, test, run, and manage Swift Package Manager projects. Use when working with Package.swift projects, running "swift build", "swift test", or "swift run", managing package executables, or cleaning SPM build artifacts.
---

> **Xcode MCP**: If the package is open in Xcode and `BuildProject` is in your tool list, prefer that over this skill.

# Swift Package

Manage Swift Package Manager projects.

## Prerequisites

For build/test output parsing: `brew install xcsift`

## Build & Test (with xcsift)

Always use the sandbox wrapper to isolate the SPM cache from Xcode:

```bash
cd /path/to/package

# Build
$(cat /tmp/claude-sandbox-$(echo $PPID))/bin/swift build 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings

# Build release
$(cat /tmp/claude-sandbox-$(echo $PPID))/bin/swift build -c release 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings

# Test
$(cat /tmp/claude-sandbox-$(echo $PPID))/bin/swift test 2>&1 | tee /tmp/test.log | xcsift --format toon --warnings

# Test with filter
$(cat /tmp/claude-sandbox-$(echo $PPID))/bin/swift test --filter "testLogin" 2>&1 | tee /tmp/test.log | xcsift --format toon --warnings
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
$(cat /tmp/claude-sandbox-$(echo $PPID))/bin/swift package clean

# Or remove .build directory directly
rm -rf /path/to/package/.build
```

Output from `xcsift --format toon`: token-optimized output with errors and warnings. Check log files for full output.
