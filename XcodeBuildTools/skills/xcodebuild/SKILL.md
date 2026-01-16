---
name: xcodebuild
description: Build Xcode projects for simulator, device, or macOS using `xcodebuild` with xcsift for token-efficient output. Use when compiling iOS/tvOS/watchOS apps, building macOS apps, cleaning build products or before you invoke any Bash command with `xcodebuild` or `swift`.
---

# Xcodebuild

Build Xcode projects and workspaces using `xcodebuild` with `xcsift --format toon --warnings --executable` for token-efficient output.

The `--executable` flag shows the path to the built executable, which you'll need if you want to run the app afterwards.

## Prerequisites

Ensure `xcsift` is installed and up to date: `brew install xcsift` (or `brew upgrade xcsift` to update).

## Key Constraints

1. **Never use `-sdk` parameter** - causes unnecessary build failures
2. **Always add** `-skipMacroValidation -skipPackagePluginValidation`
3. **iOS/watchOS/tvOS**: Must specify destination with simulator ID. Don't try to guess a simulator name or id, use `xcrun simctl list devices available` to find a valid one.
4. **macOS**: Use `-destination 'platform=macOS'` or omit destination
5. **Single line commands** Do not use line continuation characters (backslashes) to split commands across multiple lines. Keep each command on a single line.
6. **Capture full output just in case** `xcsift` only outputs the most important build information but in some cases you might need to inspect the full output of `xcodebuild`. When using `xcsift` always `tee` to a temporary file and use it if `xcsift`'s output is not enough. In the examples below the path to the temporary file is an example, use what you think is the most appropriate location.
7. **Always use workspace when building** Always use the `-workspace` flag to build, never `-project`

## Build Command Examples

These are examples of common operation. Feel free to change them but always remember the constraints above.

### iOS Simulator
```bash
# Find simulator
xcrun simctl list devices available

# Build
xcodebuild -workspace MyApp.xcworkspace -scheme MyApp -destination 'id=<simulator-uuid>' -skipMacroValidation -skipPackagePluginValidation build 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings --executable
```

### Physical Device
```bash
xcodebuild -workspace MyApp.xcworkspace -scheme MyApp -destination 'id=<device-udid>' -skipMacroValidation -skipPackagePluginValidation build 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings --executable
```

### macOS
```bash
xcodebuild -workspace MyApp.xcworkspace -scheme MyApp -destination 'platform=macOS' -skipMacroValidation -skipPackagePluginValidation build 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings --executable
```

### Clean
```bash
xcodebuild -workspace MyApp.xcworkspace -scheme MyApp clean 2>&1 | xcsift --format toon
```

## Output

`xcsift --format toon --warnings --executable` returns token-optimized output with errors, warnings, and notes. Check `/tmp/build.log` for full output if needed.
