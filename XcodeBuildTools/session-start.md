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

<!-- IF_XCODE_MCP -->
## Xcode MCP Integration

The Xcode MCP server is available, but XcodeBuildTools remains the primary routing surface for build, test, Swift package, and project-inspection workflows.

Do not bypass an applicable XcodeBuildTools skill just because overlapping Xcode MCP tools are visible. Use raw Xcode MCP tools only when:
- the user explicitly asks to use Xcode MCP,
- no XcodeBuildTools skill covers the requested task,
- the task needs MCP-only Xcode context, such as live editor or project state,
- or the selected XcodeBuildTools skill explicitly instructs you to use MCP for that step.

### Routing Rules

| Domain | Primary route | Raw Xcode MCP use |
|--------|---------------|-------------------|
| Building | `xcodebuild` skill | Only when explicitly requested or required by the skill |
| Testing | `xcode-test` skill | Only when explicitly requested or required by the skill |
| Project inspection | `xcode-project` skill | Use MCP for live Xcode/editor state that the skill cannot inspect |
| SPM | `swift-package` skill | Only when explicitly requested or required by the skill |
| Documentation | `sosumi` MCP server | `DocumentationSearch` is fine when available |

**How to route**: Start with the applicable XcodeBuildTools skill. Use raw Xcode MCP directly only for MCP-only work or explicit user requests.

### Always Use XcodeBuildTools (No MCP Equivalent)

These skills have no Xcode MCP equivalent — always use them directly:
- `device-app` — Install/launch apps on physical devices
- `sim-log` — Capture iOS Simulator logs
- `xcode-doctor` — Xcode environment diagnostics
- `macos-app` — macOS application lifecycle management
- `sparkle-integration` — Sparkle auto-update framework

### Future Xcode MCP Tools

New Xcode MCP tools do not automatically override XcodeBuildTools routing. Prefer the XcodeBuildTools skill unless the new MCP tool provides a capability the skill does not cover or the user explicitly asks for it.
<!-- END_XCODE_MCP -->

<!-- IF_NO_XCODE_MCP -->
## Documentation

The `sosumi` MCP server provides quick access to Apple's official documentation for Swift, SwiftUI, UIKit, and other frameworks. Use it for new APIs or to verify the correct parameters.
<!-- END_NO_XCODE_MCP -->
