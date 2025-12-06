---
name: swift-package
description: Build, test, run, and manage Swift packages (SPM). Use this skill when working with Swift Package Manager projects.
---

# Swift Package

Build, test, run, and manage Swift Package Manager (SPM) packages.

## Prerequisites

- macOS with Xcode or Swift toolchain installed
- A Swift package (directory containing Package.swift)

## Scripts

All scripts are in the `scripts/` directory and output JSON.

### swift-build.py

Build a Swift package.

```bash
# Build in debug mode
scripts/swift-build.py --path /path/to/package

# Build in release mode
scripts/swift-build.py --path /path/to/package --configuration release

# Build specific target
scripts/swift-build.py --path /path/to/package --target MyLibrary

# Build for specific architecture
scripts/swift-build.py --path /path/to/package --arch arm64
```

**Parameters:**
- `--path`: Path to Swift package (default: current directory)
- `--configuration`: Build mode (debug or release, default: debug)
- `--target`: Specific target to build
- `--arch`: Target architecture (arm64 or x86_64)

### swift-test.py

Run Swift package tests.

```bash
# Run all tests
scripts/swift-test.py --path /path/to/package

# Run specific test
scripts/swift-test.py --path /path/to/package --filter "MyTests.testSomething"

# Run with coverage
scripts/swift-test.py --path /path/to/package --enable-code-coverage
```

### swift-run.py

Build and run a Swift package executable.

```bash
# Run default executable
scripts/swift-run.py --path /path/to/package

# Run specific executable
scripts/swift-run.py --path /path/to/package --target MyCLI

# Pass arguments to executable
scripts/swift-run.py --path /path/to/package --target MyCLI -- --verbose input.txt
```

### swift-clean.py

Clean Swift package build artifacts.

```bash
scripts/swift-clean.py --path /path/to/package
```

### swift-package-info.py

Show Swift package information.

```bash
# Show package description
scripts/swift-package-info.py --path /path/to/package

# Show dependencies
scripts/swift-package-info.py --path /path/to/package --show-dependencies
```

## Typical Workflow

```bash
# 1. Check package info
scripts/swift-package-info.py --path .

# 2. Build the package
scripts/swift-build.py --path .

# 3. Run tests
scripts/swift-test.py --path .

# 4. Run the executable (if any)
scripts/swift-run.py --path . --target MyCLI

# 5. Build for release
scripts/swift-build.py --path . --configuration release
```

## Notes

- Swift packages are identified by the presence of a `Package.swift` file
- Use `swift package resolve` to fetch dependencies before building
- Debug builds go to `.build/debug/`, release builds to `.build/release/`
