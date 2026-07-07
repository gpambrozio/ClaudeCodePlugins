# OpenCode Plugin Compatibility Fixes Design

## Goal

Complete the OpenCode adapter's Claude-compatible MCP environment contract, make the JavaScript runtime checks mandatory, and then perform a second independent code review of the resulting branch.

## Scope

This change addresses three confirmed review findings:

1. Local MCP subprocesses must receive `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PROJECT_DIR` even when the plugin's `.mcp.json` does not declare them explicitly.
2. `${CLAUDE_PLUGIN_DATA}` must resolve to a stable, writable per-plugin directory and be exported to local MCP subprocesses.
3. The repository test gate must fail when Node.js is unavailable instead of silently skipping every OpenCode runtime, syntax, and export check.

Generated `*/common/opencode-plugin.js` copies will continue to be produced from `common/opencode-plugin.js` by `scripts/sync-plugin-common.py`; they will not be edited directly.

## Compatibility Context

`createOpenCodePlugin` will construct one MCP compatibility context per plugin instance containing:

- `pluginRoot`: the normalized plugin installation directory.
- `projectDir`: OpenCode's worktree when present, otherwise its directory.
- `pluginData`: a stable path derived from the plugin's manifest name.

The data root will be `$XDG_DATA_HOME/opencode/plugin-data` when `XDG_DATA_HOME` is set, otherwise `~/.local/share/opencode/plugin-data`. The plugin identifier will use the manifest name, falling back to the plugin directory name, with characters outside `A-Z`, `a-z`, `0-9`, `_`, and `-` replaced by `-`. This mirrors the compatibility contract's stable, sanitized identifier behavior without writing into the plugin checkout.

The data directory will be created lazily when a configuration references `CLAUDE_PLUGIN_DATA` or when a local MCP server is registered. Remote-only plugins that never use the variable will not create state on disk.

## MCP Translation

Local MCP translation will expand the source server's explicit `env` or `environment` record, then add these host-owned values:

- `CLAUDE_PLUGIN_ROOT`
- `CLAUDE_PLUGIN_DATA`
- `CLAUDE_PROJECT_DIR`

The compatibility values take precedence over same-named entries in `.mcp.json`, keeping them authoritative and preventing a plugin configuration from publishing paths inconsistent with the host context. Other explicit environment entries remain unchanged.

`mcpVariable` will resolve all three compatibility placeholders before falling back to `process.env`. Existing required-variable and default-value behavior remains unchanged for ordinary environment variables.

If the data directory cannot be created, MCP registration will fail with the underlying filesystem error. This matches the existing behavior for required placeholders and avoids registering a server with a nonfunctional persistence path.

## Mandatory Node.js Gate

The test suite will contain an explicit repository-integrity check that requires `node` on `PATH`. The existing runtime, syntax, and export tests may retain defensive skips for direct isolated invocation, but the prescribed repository command will fail overall before a missing Node.js runtime can produce a false-green result.

This keeps local failure output clear and avoids coupling the production adapter to a test-only executable lookup helper.

## Test Strategy

Implementation will follow red-green TDD:

1. Add a runtime test proving a local MCP server receives all three compatibility environment variables and that host-owned values override conflicting source entries.
2. Run that focused test and confirm it fails because the variables are absent.
3. Add a runtime test proving `${CLAUDE_PLUGIN_DATA}` expands under a temporary `XDG_DATA_HOME`, creates the directory, and remains stable across plugin instances.
4. Run that focused test and confirm it fails because `CLAUDE_PLUGIN_DATA` is currently unresolved.
5. Add the mandatory Node.js repository-integrity assertion and reproduce the old false-green behavior with Node removed from `PATH` before changing the gate.
6. Implement the minimal adapter and test-gate changes, regenerate common helper copies, and rerun focused tests after each fix.
7. Run `python3 -m unittest discover -s tests -v`, `python3 scripts/sync-plugin-common.py --check`, and `git diff --check 3d176af9d7cf82ab907747a27636b285546a9a07`.

## Second Review

After all tests pass, independent read-only reviews will cover:

- MCP compatibility and path lifecycle behavior.
- Sandbox and plugin runtime regressions.
- Packaging, generated-copy integrity, documentation, and test-gate behavior.

Every additional finding must be reproduced or supported by a concrete code path, must have been introduced by this branch, and must receive its own regression test before being fixed. The full verification suite will run again after any follow-up changes.
