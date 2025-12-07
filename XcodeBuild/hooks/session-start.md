# Xcode Build Plugin

The `XcodeBuild` plugin provides specialized skills for Xcode project building, testing, and deployment. Use these capabilities appropriately:

## Building, Testing & Compilation

**IMPORTANT**: Whenever you need to build or test an Xcode project/workspace, compile or test Swift packages, or anytime you would use `swift`/`xcodebuild` commands, **always** use the `xcodebuild` skill instead. This skill provides token-efficient, AI-friendly compilation output using [xcsift](https://github.com/ldomaradzki/xcsift).

## Available Skills

| Skill | Description |
|-------|-------------|
| `swift-package` | Build, test, run, and manage Swift Package Manager projects |
| `xcode-project` | Discover projects, list schemes, view settings, get bundle IDs |
| `xcodebuild` | Build for simulator, device, or macOS; clean build products |
| `xcode-test` | Run unit and UI tests |
| `xcode-doctor` | Diagnose Xcode development environment |
| `device-app` | Manage apps on physical Apple devices |
| `macos-app` | Launch and stop macOS applications |
| `sim-log` | Capture logs from iOS Simulator apps |
