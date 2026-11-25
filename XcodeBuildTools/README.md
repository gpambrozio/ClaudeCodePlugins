# XcodeBuildTools

Xcode development tools for Claude Code-compatible agents. Build/test tools use [xcsift](https://github.com/ldomaradzki/xcsift) for token-efficient JSON output.

## Installation

Claude Code:

```bash
/plugin marketplace add gpambrozio/ClaudeCodePlugins
/plugin install XcodeBuildTools@ClaudeCodePlugins
```

OpenCode:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "/path/to/ClaudeCodePlugins/XcodeBuildTools/opencode-plugin.js"
  ]
}
```

Restart OpenCode after changing config. The OpenCode entry point registers this plugin's skills, `sosumi` MCP server, session context, command guardrails, Xcode MCP auto-approval helper, and Xcode build sandbox environment. Xcode MCP first routing and the per-worktree sandbox are Claude Code features: OpenCode sessions get the default skills-first context and the per-session sandbox pool.

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
| `swift-code-analysis` | Review Swift code for architecture, correctness, and maintainability issues |
| `swiftui-modernize` | Review SwiftUI files for deprecated APIs and modernization opportunities |

## Xcode MCP Integration

Xcode 26.3 and later ship an MCP server (`xcrun mcpbridge`). By default XcodeBuildTools stays the primary route for build, test, Swift package and project-inspection work even when Xcode MCP tools are visible, and keeps raw Xcode MCP use for explicit requests, live editor or project state, and gaps no skill covers. Projects can opt in to the opposite: **Xcode MCP first**.

### Opting a project in to Xcode MCP first

Set `XCODEBUILDTOOLS_PREFER_MCP` in the project's committed `.claude/settings.json`:

```json
{
  "env": {
    "XCODEBUILDTOOLS_PREFER_MCP": "1"
  }
}
```

The SessionStart hook reads the variable from the environment first, then from the project's `.claude/settings.local.json` and `.claude/settings.json`. `1`, `true`, `yes` and `on` opt in; `0`, `false`, `no` and `off` opt out, so `"XCODEBUILDTOOLS_PREFER_MCP": "0"` in `settings.local.json` turns it off for one checkout. Without the setting, the session context is 0.5.11's except for the two Build Isolation paragraphs, which now describe the per-worktree sandbox; a test compares it with a frozen copy of the 0.5.11 output.

The project also needs the Xcode MCP server configured for the agent, for example in its `.mcp.json`:

```json
{
  "mcpServers": {
    "xcode": { "type": "stdio", "command": "xcrun", "args": ["mcpbridge"] }
  }
}
```

The plugin does not ship this server itself, so projects that have not opted in never start `mcpbridge`.

When a project opts in and the MCP is usable, the session context tells the agent to:

- note which `.xcscheme` files are already modified, then open this worktree's workspace (the hook finds it and prints its absolute path) with `XcodeOpenWorkspace`, keep the `workspace-…` id it returns and pass that id as `workspaceIdentifier` on every call (headless tools reject the absolute path with "Unknown workspace identifier"), keep to one tool per worktree, and close it with `XcodeCloseWorkspace` at the end;
- after closing, check `git status`: `git restore` a shared `.xcscheme` the close rewrote only if it was clean before and the task didn't change it, and otherwise undo just the lines the close added;
- pass `RunSomeTests` one identifier per test: a whole suite as one identifier runs but reports a single "No result" with no counts;
- use the MCP for builds (`BuildProject`), runs (`RunProject`), focused tests and test plans (`RunSomeTests`, `RunAllTests`), previews (`RenderPreview`) and console logs (`GetConsoleOutput`);
- fall back to the skills for what the MCP cannot do: a destination chosen by UDID, `TEST_RUNNER_*` variables, `-skip-testing`, `-collect-test-diagnostics`, result bundle paths, archives and exports, scripts and CI, physical devices (`device-app`), Swift packages from the command line (`swift-package`), `xcode-doctor`, `sparkle-integration`, `sim-log` for apps the MCP did not launch, and `macos-app`.

If the MCP is not usable, the agent gets the default skills-first context plus a notice that says why. That includes Xcode 26.x: its bridge has no `XcodeOpenWorkspace` and addresses open windows by `tabIdentifier`, so MCP-first routing needs Xcode 27 or later.

### Headless and windowed modes

| Mode | Detected by | Approvals |
|------|-------------|-----------|
| Headless (Xcode 27+) | `xcrun mcp-server status --format json` reports `permission.enabled` | The owner runs `sudo xcrun mcp-server approve <id>` and `allow-folder`; there is no dialog |
| Windowed (Xcode 27+) | The status reports headless mode off, and Xcode is running | Xcode's "Allow" dialog, clicked by the auto-approve hook below |
| Unavailable | No `mcpbridge`; Xcode 26.x (no `xcrun mcp-server`); a status probe that fails, times out (5 seconds) or prints no JSON; or headless off and Xcode not running | The agent uses the skills; the notice says why and names the command to run (`sudo xcrun mcp-server enable`) |

Headless mode shows the pending requests from `xcrun mcp-server status`, both in the agent's context and in the session's system message, with the exact command for each (`--always` for signed agents and folders, `--for-24-hours` for unsigned agents). Folder requests for other checkouts are left out, including a git worktree nested inside this one (such as `.worktrees/feature`); a request for a folder that contains this checkout is kept. The agent is told never to run sudo, enable the server or approve anything itself.

### One-time setup for headless mode (owner)

```bash
sudo xcrun mcp-server enable                                # if `xcrun mcp-server status` says headless is off
sudo xcrun mcp-server allow-folder /path/to/worktrees --always   # a parent folder covers every worktree under it
xcrun mcp-server status                                     # after the agent first opens a workspace: shows the pending request id
sudo xcrun mcp-server approve <id> --always                 # signed agents; unsigned ones take --for-24-hours
```

### Auto-Approve Hook (windowed mode only)

A backgrounded SessionStart hook clicks "Allow" on the windowed Xcode MCP authorization dialog. It:
- Runs only when Xcode is running and `mcpbridge` exists
- Clicks only in positively established windowed mode: Xcode 26.x, or Xcode 27 whose `xcrun mcp-server status` answers within 5 seconds with headless permission disabled. It does nothing when headless mode is enabled or the status probe fails, stalls or prints no JSON
- Does not require host-level `async` hook support
- Times out silently if no dialog appears

**Prerequisite**: Grant Accessibility access to your terminal app in System Settings > Privacy & Security > Accessibility. The script will prompt you if this is missing.

## Build Isolation

The plugin's `bin/xcodebuild` and `bin/swift` wrappers shadow `/usr/bin` and pass `-derivedDataPath`, `-clonedSourcePackagesDirPath` and `--cache-path` so command-line builds never share DerivedData or the SPM cache with Xcode. In Claude Code the sandbox is `$TMPDIR/claude-sandbox/wt-<name>-<hash>/`, keyed by the worktree's git directory (or the project folder outside git): every session in the same worktree builds warm, and separate worktrees stay separate. Two agents in one worktree share it, so keep to one agent per worktree. Sandboxes of removed worktrees are deleted at the next session start, and a sandbox unused for three days is reset on its next build. The OpenCode entry point keeps its own per-session sandbox pool.

Xcode MCP builds use Xcode's own DerivedData, not this sandbox.

## Related Plugins

- **iOSSimulator** - Simulator control, screenshots, video, status bar
- **SwiftScaffolding** - Swift project scaffolding through XcodeBuildMCP

## Changelog

### 0.6.0
- Xcode MCP first, per project: a project opts in with `XCODEBUILDTOOLS_PREFER_MCP=1` in the `env` of its `.claude/settings.json` (also read from the environment and `.claude/settings.local.json`). Opted-in sessions get MCP-first routing (build, run, focused tests, test plans, previews and console logs through the Xcode MCP, opening the worktree's workspace by its path and passing the `workspace-…` id `XcodeOpenWorkspace` returns as `workspaceIdentifier`, checking `git status` after `XcodeCloseWorkspace` and undoing only the `.xcscheme` changes the close made) and a shorter fallback list for what the MCP cannot do. MCP-first routing needs Xcode 27's workspace tools; Xcode 26.x gets the skills-first context with a notice. Projects that don't opt in get 0.5.11's routing; only the Build Isolation paragraphs of their context changed, to describe the per-worktree sandbox
- Xcode 27 headless MCP detection through `xcrun mcp-server status --format json`, alongside the windowed Xcode 26.3+ bridge. The context says when the MCP is unavailable or awaiting approval, lists pending requests for this checkout, and prints the exact `sudo xcrun mcp-server` commands the owner must run. The plugin never runs sudo or approves anything
- The auto-approve hook clicks only in windowed mode it can establish (Xcode 26.x, or Xcode 27 reporting headless mode off within 5 seconds); headless mode or a failed or stalled status probe leaves it idle
- The build sandbox is keyed per worktree (`$TMPDIR/claude-sandbox/wt-<name>-<hash>`) instead of per session, so new sessions in the same worktree build warm. Separate worktrees stay separate. The SessionEnd teardown hook (`teardown-sandbox.py`) and `/clear` inheritance are gone; sandboxes of removed worktrees are swept at session start, sandboxes unused for three days are reset on their next build, and per-session sandboxes from older versions are removed once their session has exited
- Skill routing notes now defer to the Xcode MCP for plain builds and tests in opted-in projects
- The OpenCode entry point registers skills, MCP servers, session-start context and command guardrails as before, and keeps the default routing and its per-session sandbox pool

### 0.5.11
- Added `opencode-plugin.js` for OpenCode users
- The OpenCode entry point registers skills, MCP servers, session-start context, pre-tool-use command guardrails, the Xcode MCP auto-approval helper, and the Xcode build sandbox shell environment

### 0.5.10
- Migrated the legacy analyze and SwiftUI modernization prompts to `swift-code-analysis` and `swiftui-modernize` skills
- Released self-contained common helper copies so the plugin package no longer depends on repository-level symlinks, while keeping hook configuration in `hooks/hooks.json` instead of generated `common/hooks.json` templates
- Preserved the host hook owner PID when launching SessionStart helpers in the background so sandbox inheritance across `/clear` can keep finding the prior anchor

### 0.5.9
- Keep XcodeBuildTools skills as the primary routing surface even when raw Xcode MCP tools are visible
- Clarify that raw Xcode MCP should be used for explicit user requests, MCP-only Xcode context, or gaps not covered by a skill
- Remove skill and session-start wording that told agents to prefer raw Xcode MCP over the corresponding XcodeBuildTools skill
- Clarify session-start routing across `xcodebuild`, `xcode-test`, and `swift-package`
- Make guidance and script comments more agent-neutral for Claude Code-compatible hosts
- Let Sparkle release notes generation fall back from the `claude` CLI to `codex exec` before using commit-list notes

### 0.5.8
- Sandbox environment injection migrated from a per-Bash `PreToolUse` hook (`inject-session-id.py`) to the new `CLAUDE_ENV_FILE` mechanism. `PATH`, `SANDBOX_DERIVED_DATA`, and `SANDBOX_PACKAGES` are now written once at SessionStart by a new sync hook (`write-env.sh`) and persist across every subsequent Bash command — no more per-command prefix injection
- Removed `inject-session-id.py` and the `PreToolUse`/Bash hook entry it relied on (~90 lines of Python deleted)
- Anchor-discovery for `/clear` inheritance extracted into a shared `hooks/lib/sandbox.sh` helper. Both the sync `write-env.sh` (which embeds the anchor path in `$CLAUDE_ENV_FILE`) and the async `setup-sandbox.sh` (which creates the symlink to the anchor) now go through the same `find_anchor` function, eliminating the risk of silent drift between them
- `setup-sandbox.sh` switched from inline Python to `jq` for stdin JSON parsing, matching the new hook
- No user-visible behavior change — the sandbox isolation works identically; this is an internal architecture cleanup

### 0.5.7
- Fix: sandbox inheritance across `/clear` no longer breaks SPM binary-target builds (Sparkle.xcframework and friends) or Xcode's explicit-module caches. The prior implementation renamed the sandbox directory to the new session's UUID, which left state files inside (`packages/workspace-state.json`, `build/CompilationCache.noindex/**/*.leaf`, `build/ModuleCache.noindex/`, `build/Build/Intermediates.noindex/`) pointing at the old on-disk path — causing errors like `There is no XCFramework found at '.../claude-sandbox/<OLD_SESSION_ID>/packages/artifacts/...'` on the first build after `/clear`, and forcing users to delete DerivedData by hand
- Inheritance is now a **symlink** from the new session-id to the original anchor directory, so every embedded absolute path keeps resolving. The anchor's on-disk name stays stable for the lifetime of the Claude process
- Setup's peer sweep is symlink-aware: dangling symlinks, dead-owner symlinks, and our own leftover symlinks from prior `/clear`s are cleaned up; real directories are only removed once no live symlink still references them
- `teardown-sandbox.py` (SessionEnd) is symlink-aware: when the sandbox path is a symlink, the symlink is unlinked first, and the anchor is GC'd only if no other live symlink under `$TMPDIR/claude-sandbox` still resolves to it
- `bin/xcodebuild` and `bin/swift` now read `$SANDBOX_DERIVED_DATA` and `$SANDBOX_PACKAGES` directly instead of reconstructing paths from `$CLAUDE_SESSION_ID`; the PreToolUse `inject-session-id` hook no longer injects `CLAUDE_SESSION_ID` into Bash commands (single source of truth for the sandbox paths is the hook's two `SANDBOX_*` exports)

### 0.5.6
- Sandbox wrappers renamed `bin/xcodebuild-sandbox` → `bin/xcodebuild` and `bin/swift-sandbox` → `bin/swift`. They now shadow `/usr/bin/xcodebuild` and `/usr/bin/swift`, so nested calls from Makefiles, fastlane lanes, and other build scripts are sandboxed transparently — not just direct Claude invocations
- `inject-session-id` PreToolUse hook now prepends the plugin's `bin/` to `PATH` (Claude Code appends plugin bin dirs, which left the wrappers behind `/usr/bin`) and exports `CLAUDE_SESSION_ID` on every Bash command so indirect invocations (e.g. `./build.sh`) inherit both the wrappers and the sandbox key
- Hook also exports `SANDBOX_DERIVED_DATA` and `SANDBOX_PACKAGES` pointing at the per-session DerivedData and cloned SPM paths — scripts that need to locate built `.app` bundles, xcresults, test products, or package checkouts can use them instead of reconstructing the formula
- Skills updated to use bare `xcodebuild` / `swift` names

### 0.5.5
- `inject-session-id` PreToolUse hook now only exports `CLAUDE_SESSION_ID` when a Bash command actually references `xcodebuild-sandbox` or `swift-sandbox` — no more prefixing every unrelated Bash invocation

### 0.5.4
- Sandbox wrappers are now static `bin/xcodebuild-sandbox` and `bin/swift-sandbox` scripts (added to PATH automatically), replacing dynamically generated scripts in `$TMPDIR`
- Sandbox keyed by Claude session ID (`$CLAUDE_SESSION_ID`, injected into every Bash invocation via a `PreToolUse` hook) instead of `$PPID` — the latter is not stable across hook and Bash-tool execution contexts
- Added `SessionEnd` hook (`teardown-sandbox.py`) to clean up sandbox directories when the session ends
- Simplified `setup-sandbox.sh` — creates per-session directories keyed by session ID; pointer file removed

### 0.5.3
- Removed auto-update hook from SessionStart to prevent configuration issues

### 0.5.2
- Add `--executable` flag to xcsift in `swift-package` and `xcode-test` skills for consistent executable path output across all skills

### 0.5.1
- Restored auto-update hook
- Version tracking now uses CLAUDE_PLUGIN_DATA with migration from old .claude/ directory

### 0.5.0
- Build isolation sandbox: CLI builds use isolated DerivedData and SPM cache via wrapper scripts

### 0.4.1
- Removed auto-update hook from SessionStart

### 0.4.0
- Xcode MCP compatibility: auto-detects Xcode 26.3+ native MCP server at session start
- Conditional MCP routing guidance for build, test, project inspection, and documentation when raw Xcode MCP tools are available
- Auto-approve hook: automatically clicks "Allow" on Xcode's MCP authorization dialog (async, PID-locked)
- Future-proofing: generic routing guidance for new Xcode MCP tools beyond the known set
- MCP notes added to all 9 skills indicating routing or uniqueness

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
