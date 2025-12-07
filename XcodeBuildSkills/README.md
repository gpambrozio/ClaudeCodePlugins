# XcodeBuildSkills

Xcode development skills for Claude Code, reimplementing tools from [XcodeBuildMCP](https://github.com/cameroncooke/XcodeBuildMCP) as executable Python scripts.

## Installation

```bash
/plugin marketplace add gpambrozio/ClaudeCodePlugins
/plugin install XcodeBuildSkills@ClaudeCodePlugins
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

All scripts output JSON and support `--help`.

## Related Plugins

- **iOSSimulator** - Simulator control, screenshots, video, status bar
- **SwiftDevelopment** - swift-compile with xcswift integration

## License

MIT
