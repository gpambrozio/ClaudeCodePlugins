---
name: xcode-test
description: Run Xcode unit tests and UI tests using xcodebuild. Use when running tests for iOS/macOS projects, filtering specific test cases, or checking test results.
---

# Xcode Test

Run unit and UI tests with xcodebuild.

## Usage

```bash
# iOS simulator tests
scripts/xcode-test.py --project <path> | --workspace <path> --scheme <name> \
  [--simulator-name "iPhone 15"] [--only-testing "Target/TestClass/testMethod"]

# macOS tests
scripts/xcode-test.py --project <path> | --workspace <path> --scheme <name> --macos
```

## Key Arguments

- `--only-testing <spec>`: Run specific tests (repeatable)
- `--skip-testing <spec>`: Skip specific tests (repeatable)
- `--simulator-name` or `--simulator-id`: Target simulator
- `--macos`: Run on macOS instead of simulator

Test spec format: `Target`, `Target/Class`, or `Target/Class/method`

Output JSON includes `success`, `tests_passed`, `tests_failed`.
