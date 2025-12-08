---
name: xcodebuild
description: Build Xcode projects for simulator, device, or macOS using xcodebuild with xcsift for token-efficient output. Use when compiling iOS/tvOS/watchOS apps, building macOS apps, or cleaning build products.
---

# Xcodebuild

Build Xcode projects and workspaces using `xcodebuild` with `xcsift --format toon` for token-efficient output.

## Prerequisites

Ensure `xcsift` is installed and up to date: `brew install xcsift` (or `brew upgrade xcsift` to update).

## Key Constraints

1. **Never use `-sdk` parameter** - causes unnecessary build failures
2. **Always add** `-skipMacroValidation -skipPackagePluginValidation`
3. **iOS/watchOS/tvOS**: Must specify destination with simulator ID
4. **macOS**: Use `-destination 'platform=macOS'` or omit destination

## Build Commands

### iOS Simulator
```bash
# Find simulator
xcrun simctl list devices available | grep "iPhone"

# Build
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'id=<simulator-uuid>' \
  -skipMacroValidation -skipPackagePluginValidation \
  build 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings
```

### Physical Device
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'id=<device-udid>' \
  -skipMacroValidation -skipPackagePluginValidation \
  build 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings
```

### macOS
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -destination 'platform=macOS' \
  -skipMacroValidation -skipPackagePluginValidation \
  build 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings
```

### Clean
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  clean 2>&1 | xcsift --format toon
```

## Output

`xcsift --format toon` returns token-optimized output with errors, warnings, and notes. Check `/tmp/build.log` for full output if needed.
