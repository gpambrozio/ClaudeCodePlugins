---
name: xcode-test
description: Run Xcode unit tests and UI tests using xcodebuild test. Supports iOS simulators and macOS. Use to run tests for Xcode projects and workspaces.
---

# Run Xcode Tests

Execute tests using xcodebuild.

## Usage

```bash
# Run on iOS simulator
scripts/xcode-test.py --project ./MyApp.xcodeproj --scheme MyAppTests --simulator-name "iPhone 15"

# Run on macOS
scripts/xcode-test.py --workspace ./MyApp.xcworkspace --scheme MyAppTests --macos
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | One required | Path to .xcodeproj file |
| `--workspace` | One required | Path to .xcworkspace file |
| `--scheme` | Yes | Scheme to test |
| `--simulator-id` | No | Simulator UDID for iOS tests |
| `--simulator-name` | No | Simulator name for iOS tests |
| `--macos` | No | Run tests on macOS |
| `--configuration` | No | Build configuration (default: Debug) |
| `--derived-data` | No | Custom derived data path |
| `--only-testing` | No | Run only specific test (can repeat) |
| `--skip-testing` | No | Skip specific test (can repeat) |

## Examples

```bash
# Run all tests
scripts/xcode-test.py --project ./MyApp.xcodeproj --scheme MyAppTests --simulator-name "iPhone 15"

# Run specific test class
scripts/xcode-test.py \
  --project ./MyApp.xcodeproj \
  --scheme MyAppTests \
  --simulator-name "iPhone 15" \
  --only-testing "MyAppTests/LoginTests"

# Run macOS tests
scripts/xcode-test.py --project ./MyApp.xcodeproj --scheme MyAppTests --macos
```

## Output

```json
{
  "success": true,
  "message": "All tests passed",
  "tests_passed": 42,
  "tests_failed": 0,
  "scheme": "MyAppTests"
}
```

## Test Specification Format

For `--only-testing` and `--skip-testing`:
- Test target: `MyAppTests`
- Test class: `MyAppTests/LoginTests`
- Test method: `MyAppTests/LoginTests/testLoginSuccess`

## Notes

- Default destination is "iPhone 15" simulator
- Tests timeout after 30 minutes
- Use `--only-testing` to run specific tests faster
