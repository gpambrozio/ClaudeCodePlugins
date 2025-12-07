# XcodeBuildSkills

Xcode development skills for Claude Code. Build/test skills use [xcsift](https://github.com/ldomaradzki/xcsift) for token-efficient JSON output.

## Installation

```bash
/plugin marketplace add gpambrozio/ClaudeCodePlugins
/plugin install XcodeBuildSkills@ClaudeCodePlugins
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

## Related Plugins

- **iOSSimulator** - Simulator control, screenshots, video, status bar
- **SwiftDevelopment** - swift-compile skill with xcsift integration

## License

MIT
