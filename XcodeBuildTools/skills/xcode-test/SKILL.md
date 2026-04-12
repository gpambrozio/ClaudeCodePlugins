---
name: xcode-test
description: Run Xcode unit tests and UI tests using xcodebuild with xcsift for token-efficient output. Use when running tests for iOS/macOS projects, filtering specific test cases, or checking test results.
---

> **Xcode MCP**: If `RunAllTests` / `RunSomeTests` / `GetTestList` are in your tool list, prefer those over this skill.

# Xcode Test

Run unit and UI tests with `xcodebuild test` and `xcsift --format toon --executable`.

## Prerequisites

Ensure `xcsift` is installed and up to date: `brew install xcsift` (or `brew upgrade xcsift` to update).

## Key Constraints

1. **Never use `-sdk` parameter** - causes unnecessary build failures
2. **Always add** `-skipMacroValidation -skipPackagePluginValidation`
3. **Single line commands** Do not use line continuation characters (backslashes) to split commands across multiple lines. Keep each command on a single line.
4. **Use workspace when available** If the project has a corresponding `xcworkspace` always use the `-workspace` flag to compile, never `-project`
5. **Always use the sandbox** Use `xcodebuild-sandbox` instead of bare `xcodebuild`. This isolates DerivedData and SPM caches from Xcode.

## Test Commands

### iOS Simulator Tests
```bash
xcodebuild-sandbox -workspace MyApp.xcworkspace -scheme MyAppTests -destination 'id=<simulator-uuid>' -skipMacroValidation -skipPackagePluginValidation test 2>&1 | tee ${TMPDIR:-/tmp}/test.log | xcsift --format toon --warnings --executable
```

### macOS Tests
```bash
xcodebuild-sandbox -workspace MyApp.xcworkspace -scheme MyAppTests -destination 'platform=macOS' -skipMacroValidation -skipPackagePluginValidation test 2>&1 | tee ${TMPDIR:-/tmp}/test.log | xcsift --format toon --warnings --executable
```

### Run Specific Tests
```bash
xcodebuild-sandbox -workspace MyApp.xcworkspace -scheme MyAppTests -destination 'id=<simulator-uuid>' -only-testing:MyAppTests/LoginTests/testLoginSuccess test 2>&1 | tee ${TMPDIR:-/tmp}/test.log | xcsift --format toon --warnings --executable
```

### Skip Specific Tests
```bash
xcodebuild-sandbox ... -skip-testing:MyAppTests/SlowTests test 2>&1 | xcsift --format toon --warnings --executable
```

## Test Specification Format

- Test target: `MyAppTests`
- Test class: `MyAppTests/LoginTests`
- Test method: `MyAppTests/LoginTests/testLoginSuccess`

Output shows test results, errors, and failures. Check `${TMPDIR:-/tmp}/test.log` for details.
