---
name: xcode-test
description: Run Xcode unit tests and UI tests using xcodebuild with xcsift for structured output. Use when running tests for iOS/macOS projects, filtering specific test cases, or checking test results.
---

# Xcode Test

Run unit and UI tests with `xcodebuild test` and `xcsift`.

## Prerequisites

Ensure `xcsift` is installed: `brew install xcsift`

## Test Commands

### iOS Simulator Tests
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyAppTests \
  -destination 'id=<simulator-uuid>' \
  -skipMacroValidation -skipPackagePluginValidation \
  test 2>&1 | tee /tmp/test.log | xcsift --warnings
```

### macOS Tests
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyAppTests \
  -destination 'platform=macOS' \
  -skipMacroValidation -skipPackagePluginValidation \
  test 2>&1 | tee /tmp/test.log | xcsift --warnings
```

### Run Specific Tests
```bash
xcodebuild \
  -workspace MyApp.xcworkspace \
  -scheme MyAppTests \
  -destination 'id=<simulator-uuid>' \
  -only-testing:MyAppTests/LoginTests/testLoginSuccess \
  test 2>&1 | tee /tmp/test.log | xcsift --warnings
```

### Skip Specific Tests
```bash
xcodebuild ... -skip-testing:MyAppTests/SlowTests test 2>&1 | xcsift --warnings
```

## Test Specification Format

- Test target: `MyAppTests`
- Test class: `MyAppTests/LoginTests`
- Test method: `MyAppTests/LoginTests/testLoginSuccess`

Output includes `success`, test counts, and any failures. Check `/tmp/test.log` for details.
