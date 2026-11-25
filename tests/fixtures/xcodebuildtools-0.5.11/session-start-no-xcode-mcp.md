# Xcode Build Tools Plugin

The `XcodeBuildTools` plugin provides specialized tools for Xcode build and test. Use these capabilities appropriately:

## Building, Testing & Compilation

**IMPORTANT**: Whenever you need to build or test an Xcode project/workspace, compile or test Swift packages, or anytime you would use `swift`/`xcodebuild` commands, **always** use the applicable XcodeBuildTools skill instead. Use `xcodebuild` for Xcode builds, `xcode-test` for Xcode tests, and `swift-package` for Swift package build/test/run workflows. These skills provide token-efficient, AI-friendly compilation output.

## Build Isolation

Each session gets an isolated build sandbox keyed by its agent session ID. The plugin ships sandboxing wrappers for `xcodebuild` and `swift` in its `bin/` directory, which is on `PATH` ahead of `/usr/bin`. Any invocation — direct (`xcodebuild ...`, `swift build ...`) or nested inside a build script (Makefile, fastlane, shell script) — is sandboxed transparently.

The wrappers inject `-derivedDataPath`, `-clonedSourcePackagesDirPath`, and `--cache-path` flags so DerivedData and SPM caches stay isolated from Xcode and from other agent sessions. No changes to commands are needed.

Two sandbox paths are also exported in every Bash invocation for scripts that need to reach into the sandbox without reconstructing the path formula:

- `$SANDBOX_DERIVED_DATA` — DerivedData root (for built `.app` bundles, xcresult files, test bundles)
- `$SANDBOX_PACKAGES` — cloned SPM packages / SwiftPM cache


## Documentation

The `sosumi` MCP server provides quick access to Apple's official documentation for Swift, SwiftUI, UIKit, and other frameworks. Use it for new APIs or to verify the correct parameters.
