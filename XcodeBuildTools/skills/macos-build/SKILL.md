---
name: macos-build
description: Build, run, and test macOS applications using Xcode. Use this skill when working with macOS app projects.
---

# macOS Build

Build, run, and test macOS applications.

## Prerequisites

- macOS with Xcode installed
- A macOS Xcode project or workspace

## Scripts

All scripts are in the `scripts/` directory and output JSON.

### build-macos.py

Build a macOS application.

```bash
# Build with workspace
scripts/build-macos.py --workspace MyApp.xcworkspace --scheme MyApp

# Build with project
scripts/build-macos.py --project MyApp.xcodeproj --scheme MyApp

# Release configuration
scripts/build-macos.py --workspace MyApp.xcworkspace --scheme MyApp --configuration Release

# Specific architecture
scripts/build-macos.py --workspace MyApp.xcworkspace --scheme MyApp --arch arm64
```

**Parameters:**
- `--workspace` or `--project`: Path to .xcworkspace or .xcodeproj (mutually exclusive)
- `--scheme`: Build scheme name (required)
- `--configuration`: Build configuration (default: Debug)
- `--arch`: Architecture (arm64 or x86_64)
- `--derived-data`: Custom derived data path
- `--extra-args`: Additional xcodebuild arguments

### build-run-macos.py

Build and run a macOS application.

```bash
scripts/build-run-macos.py --workspace MyApp.xcworkspace --scheme MyApp
```

### test-macos.py

Run tests for a macOS application.

```bash
# Run all tests
scripts/test-macos.py --workspace MyApp.xcworkspace --scheme MyAppTests

# Run specific tests
scripts/test-macos.py --workspace MyApp.xcworkspace --scheme MyAppTests --only-testing "MyAppTests/LoginTests"
```

### launch-app.py

Launch a built macOS application.

```bash
scripts/launch-app.py --app /path/to/MyApp.app

# Launch by bundle ID
scripts/launch-app.py --bundle-id com.example.myapp
```

### stop-app.py

Terminate a running macOS application.

```bash
scripts/stop-app.py --bundle-id com.example.myapp

# Force quit
scripts/stop-app.py --bundle-id com.example.myapp --force
```

## Typical Workflow

```bash
# 1. Build the app
scripts/build-macos.py --workspace MyApp.xcworkspace --scheme MyApp

# 2. Run tests
scripts/test-macos.py --workspace MyApp.xcworkspace --scheme MyAppTests

# 3. Build and run
scripts/build-run-macos.py --workspace MyApp.xcworkspace --scheme MyApp

# 4. Stop the app when done
scripts/stop-app.py --bundle-id com.example.myapp
```
