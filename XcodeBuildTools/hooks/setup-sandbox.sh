#!/bin/bash
#
# setup-sandbox.sh — Create isolated Xcode build environment (per-session)
#
# Creates per-session sandbox directories for DerivedData and SPM cache,
# isolating CLI builds from Xcode's own storage. The wrapper scripts in
# bin/ (xcodebuild, swift) read the sandbox path at runtime and inject
# the appropriate isolation flags.
#
# Each Claude Code session gets its own sandbox keyed by PPID (the Claude
# process PID). Multiple sessions can build concurrently without conflicts.
#
# The sandbox lives under $TMPDIR so it auto-cleans on reboot — no stale
# build artifacts survive a restart even if PID-based cleanup misses them.
#
# Runs as a SessionStart hook. Cleaned up by teardown-sandbox.sh on SessionEnd.

set -euo pipefail

# --- Per-session sandbox paths ---
SESSION_PID="${PPID:-$$}"
SANDBOX_ROOT="${TMPDIR:-/tmp}/claude-sandbox"
SANDBOX_BASE="$SANDBOX_ROOT/$SESSION_PID"
SANDBOX_BUILD="$SANDBOX_BASE/build"
SANDBOX_PKGS="$SANDBOX_BASE/packages"

# --- Clean up stale sessions ---
# Iterate all PID dirs under claude-sandbox/. If the owning process is dead
# (or the PID was reused by a non-Claude process), remove that session's sandbox.
if [[ -d "$SANDBOX_ROOT" ]]; then
    for session_dir in "$SANDBOX_ROOT"/*/; do
        [[ -d "$session_dir" ]] || continue
        pid=$(basename "$session_dir")
        # Skip non-numeric directory names
        [[ "$pid" =~ ^[0-9]+$ ]] || continue
        # Skip our own session
        [[ "$pid" == "$SESSION_PID" ]] && continue

        is_alive=false
        if kill -0 "$pid" 2>/dev/null; then
            pid_cmd=$(ps -o command= -p "$pid" 2>/dev/null || echo "")
            if [[ "$pid_cmd" == *claude* || "$pid_cmd" == *node* ]]; then
                is_alive=true
            fi
        fi

        if [[ "$is_alive" == "false" ]]; then
            rm -rf "$session_dir"
            rm -f "${TMPDIR:-/tmp}/claude-sandbox-$pid"
        fi
    done
fi

# --- Create sandbox directories ---
mkdir -p "$SANDBOX_BUILD" "$SANDBOX_PKGS"

# --- Write path file for skill file discovery ---
# Skill files use $(cat ${TMPDIR:-/tmp}/claude-sandbox-$(echo $PPID)) to find the sandbox.
# NOTE: $(echo $PPID) instead of bare $PPID is intentional — $PPID expands to
# empty in command position when used with pipes in Claude Code's zsh eval.
# This indirection lets the hook respect custom DerivedData locations while
# keeping skill file paths stable.
echo "$SANDBOX_BASE" > "${TMPDIR:-/tmp}/claude-sandbox-$SESSION_PID"
