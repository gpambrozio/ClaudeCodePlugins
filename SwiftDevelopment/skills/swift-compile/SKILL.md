---
name: swift-compile
description: Compiles XCode projects and swift packages and report errors or warnings. Use it whenever you would use `xcodebuild` or `swift` commands.
---

# Swift Compilation

## Instructions

Any time that you need to invoke `xcodebuild`, invoke `scripts/xcodebuild.sh` instead, using the same parameters you would pass to `xcodebuild`

Any time that you need to invoke `swift`, invoke `scripts/swift.sh` instead, using the same parameters you would pass to `swift`

## Examples

```bash
# Build a workspace
scripts/xcodebuild.sh -workspace Project.xcworkspace -scheme ProjectScheme build

# Run tests (unit tests in SPM package)
scripts/xcodebuild.sh -workspace Project.xcworkspace -scheme ProjectScheme test

# Build and run (or use Xcode's Cmd+R)
scripts/xcodebuild.sh -workspace Project.xcworkspace -scheme ProjectScheme build -configuration Debug

# Compile a swift file
scripts/swift.sh source.swift

# Test an SPM package directly
cd PackageFOlder
scripts/swift.sh test

# Build the package
scripts/swift.sh build
```

## Requirements

These script use [xcsift](https://github.com/ldomaradzki/xcsift) to parse xcodebuild and swift output into token-efficient JSON format, dramatically reducing verbosity for AI coding agents.
