---
name: swift-package-test
description: Run tests for a Swift Package using `swift test`. Use when you need to execute unit tests in a Swift Package Manager project with optional filtering, coverage, and configuration.
---

# Swift Package Test

Run Swift package tests with `swift test`.

## Usage

```bash
scripts/swift-package-test.py --package-path /path/to/package [options]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--package-path` | Yes | Path to the Swift package root directory |
| `--test-product` | No | Specific test product to run |
| `--filter` | No | Filter tests by name (regex pattern) |
| `--configuration` | No | Build configuration: `debug` (default) or `release` |
| `--no-parallel` | No | Disable parallel test execution |
| `--show-codecov` | No | Show code coverage results |
| `--parse-as-library` | No | Add `-parse-as-library` flag for `@main` support |

## Examples

```bash
# Run all tests
scripts/swift-package-test.py --package-path /path/to/MyPackage

# Run specific test product
scripts/swift-package-test.py --package-path /path/to/MyPackage --test-product MyPackageTests

# Filter tests by name
scripts/swift-package-test.py --package-path /path/to/MyPackage --filter "testLogin"

# Run with code coverage
scripts/swift-package-test.py --package-path /path/to/MyPackage --show-codecov
```

## Output

```json
{
  "success": true,
  "message": "All tests passed",
  "package_path": "/path/to/MyPackage",
  "output": "Test output..."
}
```
