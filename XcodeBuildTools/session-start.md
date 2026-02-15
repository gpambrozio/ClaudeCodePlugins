# Xcode Build Tools Plugin

The `XcodeBuildTools` plugin provides specialized tools for Xcode build and test. Use these capabilities appropriately:

## Building, Testing & Compilation

**IMPORTANT**: Whenever you need to build or test an Xcode project/workspace, compile or test Swift packages, or anytime you would use `swift`/`xcodebuild` commands, **always** use the `xcodebuild` skill instead. This skill provides token-efficient, AI-friendly compilation output.

<!-- IF_XCODE_MCP -->
## Xcode MCP Tool Delegation

The Xcode MCP server is available. **Before using an XcodeBuildTools skill, check if an equivalent Xcode MCP tool exists in your tool list.** Prefer Xcode MCP tools when available — they run inside Xcode's process and have richer project context.

### Delegation Rules

| Domain | Prefer (Xcode MCP) | Fallback (XcodeBuildTools skill) |
|--------|--------------------|---------------------------------|
| Building | `BuildProject`, `GetBuildLog` | `xcodebuild` skill |
| Testing | `RunAllTests`, `RunSomeTests`, `GetTestList` | `xcode-test` skill |
| Project inspection | `XcodeGlob`, `XcodeLS`, `XcodeListWindows` | `xcode-project` skill |
| SPM (when project open in Xcode) | `BuildProject` | `swift-package` skill |
| Documentation | `DocumentationSearch` | `sosumi` MCP server |

**How to delegate**: Before each build/test/inspection task, check your available tools. If the Xcode MCP tool is listed, use it. If not (e.g., MCP connection dropped), fall back to the corresponding XcodeBuildTools skill.

### Always Use XcodeBuildTools (No MCP Equivalent)

These skills have no Xcode MCP equivalent — always use them directly:
- `device-app` — Install/launch apps on physical devices
- `sim-log` — Capture iOS Simulator logs
- `xcode-doctor` — Xcode environment diagnostics
- `macos-app` — macOS application lifecycle management
- `sparkle-integration` — Sparkle auto-update framework

### Future Xcode MCP Tools

Beyond the specific tools listed above, if you discover additional Xcode MCP tools in your tool list that could handle a task more directly than an XcodeBuildTools skill, prefer the Xcode MCP tool. Xcode MCP tools follow naming patterns like `BuildProject`, `RunAllTests`, `Xcode*`, `Get*`, `DocumentationSearch`.
<!-- END_XCODE_MCP -->

<!-- IF_NO_XCODE_MCP -->
## Documentation

The `sosumi` MCP server provides quick access to Apple's official documentation for Swift, SwiftUI, UIKit, and other frameworks. Use it for new APIs or to verify the correct parameters.
<!-- END_NO_XCODE_MCP -->
