---
name: swift-compile
description: REQUIRED skill for building, testing, and compiling any Xcode projects, Swift packages, or iOS/macOS apps. Use this whenever you need to invoke xcodebuild or swift commands. Provides token-efficient wrappers with structured JSON output that dramatically reduce verbosity.
---

# Swift Compilation

## Overview

This skill provides token-efficient wrappers for `xcodebuild` and `swift` commands that parse output into structured JSON format, dramatically reducing verbosity for AI agents.

## When to Use This Skill

Use this skill whenever you need to:
- Build an Xcode workspace or project
- Run tests in an Xcode project
- Compile Swift Package Manager (SPM) packages
- Execute any `xcodebuild` or `swift` command

## Instructions

### For xcodebuild Commands

**ALWAYS** replace `xcodebuild` with `scripts/xcodebuild.sh` using the exact same parameters.

**IMPORTANT Constraints:**
1. **Never use `-sdk` parameter** - it can cause builds to fail unnecessarily
2. **For iOS/watchOS/tvOS targets**: You must specify a destination
   - First find available simulators: `xcrun simctl list devices available`
   - Then add: `-destination 'platform=iOS Simulator,name=<device-name>'`
   - Example device names: "iPhone 15", "iPhone 15 Pro", "Apple Watch Series 9 (45mm)"
3. **For macOS targets**: Use `-destination 'platform=macOS'` or omit destination entirely

### For swift Commands

**ALWAYS** replace `swift` with `scripts/swift.sh` using the exact same parameters.

### Interpreting Output

Both scripts output JSON with the following structure:
- `errors`: Array of compilation errors with file paths and line numbers
- `warnings`: Array of warnings
- `notes`: Additional compiler notes
- `success`: Boolean indicating build success

If the build fails, analyze the `errors` array to identify issues and suggest fixes.

## Examples

### Building an iOS App
```bash
# 1. Find available simulator
xcrun simctl list devices available | grep "iPhone"

# 2. Build with destination
scripts/xcodebuild.sh \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  build
```

### Running Tests
```bash
scripts/xcodebuild.sh \
  -workspace MyApp.xcworkspace \
  -scheme MyAppTests \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  test
```

### Building a macOS App
```bash
scripts/xcodebuild.sh \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'platform=macOS' \
  build
```

### Swift Package Manager
```bash
# Test an SPM package
cd PackageFolder
scripts/swift.sh test

# Build the package
scripts/swift.sh build

# Compile a single Swift file
scripts/swift.sh compile source.swift
```

## Requirements

These scripts use [xcsift](https://github.com/ldomaradzki/xcsift) to parse compiler output into JSON format. The scripts will attempt to install xcsift via Homebrew if not present.

## Troubleshooting

- **"No devices available"**: Install Xcode simulators via Xcode > Settings > Platforms
- **Build fails with unclear errors**: Try running the script with `-verbose` flag for full output
- **xcsift not found**: Ensure Homebrew is installed and run `brew install xcsift`
