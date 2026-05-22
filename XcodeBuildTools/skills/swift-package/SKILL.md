---
name: swift-package
description: Build, test, run, and manage Swift Package Manager projects. Use when working with Package.swift projects, running "swift build", "swift test", or "swift run", managing package executables, or cleaning SPM build artifacts.
---

> **Tool routing**: Use this skill for Swift package build/test/run workflows even when raw Xcode MCP tools are available. Use raw Xcode MCP only when explicitly requested, when this skill instructs you to, or when MCP-only Xcode context is required.

# Swift Package

Manage Swift Package Manager projects.

## Prerequisites

For build/test output parsing: `brew install xcsift`

## Build & Test (with xcsift)

**Build isolation is automatic** The plugin ships a `swift` wrapper on `PATH` ahead of `/usr/bin`, so every invocation — direct or nested inside a build script — runs inside the per-session sandbox. Just call `swift` normally.

```bash
cd /path/to/package

# Build
swift build 2>&1 | tee ${TMPDIR:-/tmp}/build.log | xcsift --format toon --warnings --executable

# Build release
swift build -c release 2>&1 | tee ${TMPDIR:-/tmp}/build.log | xcsift --format toon --warnings --executable

# Test
swift test 2>&1 | tee ${TMPDIR:-/tmp}/test.log | xcsift --format toon --warnings --executable

# Test with filter
swift test --filter "testLogin" 2>&1 | tee ${TMPDIR:-/tmp}/test.log | xcsift --format toon --warnings --executable
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

Output from `xcsift --format toon --executable`: token-optimized output with errors, warnings, and executable path. Check log files for full output.
