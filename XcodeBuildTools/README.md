# XcodeBuildTools

Xcode development tools for Claude Code. Build/test tools use [xcsift](https://github.com/ldomaradzki/xcsift) for token-efficient JSON output.

## Installation

```bash
/plugin marketplace add gpambrozio/ClaudeCodePlugins
/plugin install XcodeBuildTools@ClaudeCodePlugins
```

## Prerequisites

```bash
brew install xcsift
```

## Skills

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
| `sparkle-integration` | Integrate Sparkle 2.x auto-update framework into macOS apps |

## Xcode MCP Compatibility

Starting with v0.4.0, XcodeBuildTools automatically detects Xcode 26.3+'s native MCP server and delegates overlapping capabilities when available.

### Tool Delegation

| Domain | Xcode MCP Tool | XcodeBuildTools Fallback |
|--------|---------------|------------------------|
| Building | `BuildProject`, `GetBuildLog` | `xcodebuild` skill |
| Testing | `RunAllTests`, `RunSomeTests`, `GetTestList` | `xcode-test` skill |
| Project inspection | `XcodeGlob`, `XcodeLS`, `XcodeListWindows` | `xcode-project` skill |
| SPM (Xcode open) | `BuildProject` | `swift-package` skill |
| Documentation | `DocumentationSearch` | `sosumi` MCP server |

Skills with **no MCP equivalent** (always used directly): `device-app`, `sim-log`, `xcode-doctor`, `macos-app`, `sparkle-integration`.

### Auto-Approve Hook

The plugin includes an async hook that automatically clicks "Allow" on Xcode's MCP authorization dialog. It:
- Runs only when Xcode is active and `mcpbridge` exists
- Uses a PID-based lock file to avoid re-running for the same Xcode instance
- Times out silently after 10 seconds if no dialog appears

**Prerequisite**: Grant Accessibility access to your terminal app in System Settings > Privacy & Security > Accessibility. The script will prompt you if this is missing.

## Related Plugins

- **iOSSimulator** - Simulator control, screenshots, video, status bar
- **SwiftDevelopment** - swift-compile skill with xcsift integration

## Changelog

### 0.4.0
- Xcode MCP compatibility: auto-detects Xcode 26.3+ native MCP server at session start
- Conditional tool delegation: prefers Xcode MCP tools for build, test, project inspection, and documentation when available
- Auto-approve hook: automatically clicks "Allow" on Xcode's MCP authorization dialog (async, PID-locked)
- Future-proofing: generic fallback instruction for new Xcode MCP tools beyond the known set
- MCP notes added to all 9 skills indicating delegation preference or uniqueness

### 0.3.17
- Improved sparkle-integration security: separate Debug/Release entitlements for `disable-library-validation`
- Updated UpdaterController to use Swift's `@Observable` instead of `ObservableObject`
- Added Claude CLI integration for automatic release notes generation in `release.sh`
- Added validation checks in release script for appcast updates

### 0.3.16
- Added `sparkle-integration` skill for integrating Sparkle 2.x auto-update framework into macOS apps

### 0.3.15
- Fixed hook deduplication issue when multiple plugins installed - each plugin now has its own hooks.json

### 0.3.14
- (Version skipped)

### 0.3.13
- Improved skill matching to support `PluginName:skill` prefix format in addition to skills array

### 0.3.12
- Added skills array to info.json; improved skill matching in pre-tool-use hook

### 0.3.11
- Changed `launch-app-device.py` and `stop-app-device.py` to accept `--app` (path to .app bundle) instead of `--bundle-id`
- Bundle ID is now automatically extracted from the app's Info.plist using PlistBuddy

### 0.3.10
- Added pre-tool-use rule to warn about using `-project` instead of `-workspace`
- Improved skill/bash command matching in common infrastructure (using `in` instead of `startswith`)

### 0.3.9
- Added guidance to use `xcrun simctl list devices available` to find valid simulator IDs instead of guessing

### 0.3.8
- Added guidance to use `-workspace` instead of `-project` when workspace exists (xcodebuild and xcode-test skills)

### 0.3.7
- Improved regex pattern for swift build/test detection using word boundaries instead of trailing whitespace

### 0.3.6
- Split pre-tool-use rule into separate rules for xcodebuild and swift build/test, directing to appropriate skills

### 0.3.5
- Add `--executable` flag to xcsift commands for displaying built executable path

### 0.3.4
- Added configurable pre-tool-use rules with allow/deny/deny_once decisions and regex matching

### 0.3.3
- Added single-line command constraint to xcodebuild and xcode-test skills for consistency

### 0.3.2
- Version tracker now silently initializes on first run instead of showing entire version history

### 0.3.1
- Fixed hooks path to use plugin-local common directory (plugins cannot reference external files)

### 0.3.0
- Centralized hooks to common/hooks.json
- Made session-start.py and pre-tool-use.py self-configuring from plugin.json

### 0.2.0
- Renamed from XcodeBuildSkills to XcodeBuildTools
- Added version tracking with automatic changelog notifications on plugin updates
- Added session hooks using shared infrastructure

### 0.1.0
- Initial release with 8 Xcode development tools

## License

MIT
