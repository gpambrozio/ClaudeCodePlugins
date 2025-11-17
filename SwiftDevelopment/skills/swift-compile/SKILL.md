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

### Using `xcsift`

`xcsift` parses output from `xcodebuild` and `swift` commands and only provides the necessary data back in json format. For most cases you want to use `xcsift` to get better data out of these commands, especially when buiding and running tests.

To use `xcsift` make sure it's installed on the system. If it is not the script in `scripts/xcsift-install.sh` can be used to install it and update it if not available.

If it is already installed still try to update it before using it for the first time in a session.

If using it hides the useful output of a command (for example when trying to get all schemes) then skip using it.

This is how to use this with `xcodebuild` for example:

```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  build 2>&1 | xcsift --warnings
```

### For xcodebuild Commands

**IMPORTANT Constraints:**
1. **Never use `-sdk` parameter** - it can cause builds to fail unnecessarily
2. **Always** use the `-skipMacroValidation -skipPackagePluginValidation` parameters to avoid unnecessary error
3. **For iOS/watchOS/tvOS targets**: You must specify a destination
   - First find available simulators: `xcrun simctl list devices available`
   - Then add: `-destination 'platform=iOS/watchOS Simulator,name=<device-name>'`
   - Example device names: "iPhone 15", "iPhone 15 Pro", "Apple Watch Series 9 (45mm)"
4. **For macOS targets**: Use `-destination 'platform=macOS'` or omit destination entirely

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
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  build 2>&1 | xcsift --warnings
```

### Running Tests
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyAppTests \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  test 2>&1 | xcsift --warnings
```

### Building a macOS App
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'platform=macOS' \
  build 2>&1 | xcsift --warnings
```

### Swift Package Manager
```bash
# Test an SPM package
cd PackageFolder
swift test 2>&1 | xcsift --warnings

# Build the package
swift build 2>&1 | xcsift --warnings

# Compile a single Swift file
swift compile source.swift 2>&1 | xcsift --warnings
```

## Requirements

These scripts use [xcsift](https://github.com/ldomaradzki/xcsift) to parse compiler output into JSON format. The `script/xcsift-install.sh` can be used to install it and update it if not available.

## Troubleshooting

- **"No devices available"**: Install Xcode simulators via Xcode > Settings > Platforms
- **Build fails with unclear errors**: Try running the script with `-verbose` flag for full output
- **xcsift not found**: Ensure Homebrew is installed and run `brew install xcsift`
