# Xcode Build Tools Plugin (Xcode MCP first)

This project opted in to Xcode MCP first routing (`XCODEBUILDTOOLS_PREFER_MCP`). Xcode's MCP server ({{MCP_MODE}}) is the default for the interactive loop; the XcodeBuildTools skills cover what it cannot do. Project and repository instructions still win where they are more specific.

## Workspace

{{WORKSPACE}}

- Open it with `XcodeOpenWorkspace` before the first Xcode MCP call, and pass that absolute path as `workspaceIdentifier` on every call. Each git worktree is its own workspace; never open or drive another checkout's workspace.
- Use one tool per worktree: the Xcode MCP for the loop below, xcodebuild only for the fallbacks. Don't alternate the two for the same builds.
- Scheme, run destination and test plan are workspace state on the server. Set them with `XcodeSwitchScheme` and `XcodeSwitchRunDestination` (destinations are chosen by display title, not UDID). `XcodeSwitchTestPlan` changes the scheme's active test plan persistently, so check `git status` after it.
- When the task is finished, close the workspace with `XcodeCloseWorkspace`.

{{APPROVAL}}

## Use the Xcode MCP for

| Task | Xcode MCP tools |
|------|-----------------|
| Build | `BuildProject`, `GetBuildLog` |
| Run the app | `RunProject`, `GetConsoleOutput` |
| Focused tests, whole plans | `GetTestList`, `RunSomeTests`, `RunAllTests` |
| SwiftUI previews | `RenderPreview` |
| Console logs of an app the MCP launched | `GetConsoleOutput` |
| Documentation | `DocumentationSearch`, or the `sosumi` MCP server |

If the Xcode MCP tools are not in this session's tool list, the server is not configured for this project: tell the owner (a project `.mcp.json` entry `{"xcode": {"type": "stdio", "command": "xcrun", "args": ["mcpbridge"]}}` adds it) and use the skills. If a call returns an empty or failed reply, retry it once, then use the matching skill.

## Use the XcodeBuildTools skills for

- A destination picked by UDID (a specific simulator clone or a device): `xcodebuild`, `xcode-test`
- `TEST_RUNNER_*` environment variables, `-skip-testing`, `-collect-test-diagnostics` or a result bundle path: `xcode-test`
- Archives and exports, and anything a script or CI runs: `xcodebuild` (scripts that call `xcodebuild` run as they are)
- Physical devices: `device-app`; Swift packages from the command line: `swift-package`; environment problems: `xcode-doctor`; Sparkle: `sparkle-integration`; logs of an app the MCP did not launch: `sim-log`; launching and stopping a built macOS app: `macos-app`
- Every task when the Xcode MCP is unavailable or this agent is not approved

Whenever you do run `xcodebuild` or `swift build`/`swift test`, go through the matching skill: it pipes the output through xcsift.

## Build Isolation

Bash `xcodebuild` and `swift` calls go through the plugin's wrappers, which build into a sandbox kept per worktree (`$SANDBOX_DERIVED_DATA`, `$SANDBOX_PACKAGES`), so a new session in the same worktree builds warm. Xcode MCP builds use Xcode's own DerivedData, not the sandbox.
