#!/bin/bash
#
# setup-sandbox.sh — Prepare this worktree's isolated Xcode build sandbox
#
# Creates the sandbox directories for DerivedData and the SPM cache,
# isolating CLI builds from Xcode's own storage and from other worktrees.
# The wrapper scripts in bin/ (xcodebuild, swift) read $SANDBOX_DERIVED_DATA
# and $SANDBOX_PACKAGES at runtime and inject the isolation flags;
# hooks/write-env.sh writes those env vars to $CLAUDE_ENV_FILE during
# SessionStart.
#
# The sandbox is keyed per worktree (hooks/lib/sandbox.sh), so it outlives
# the session on purpose: the next session in the same worktree builds
# warm. There is no SessionEnd teardown. Instead this script, launched in
# the background at every SessionStart:
#
#   1. Prepares this worktree's sandbox and records which worktree owns it
#      (the `worktree` file holds sandbox_identity: the git dir, or the
#      project folder outside git).
#   2. Removes peer `wt-*` sandboxes whose worktree no longer exists, e.g.
#      after `git worktree remove`.
#   3. Removes sandboxes left by versions before 0.6.0 (keyed per session,
#      with an owner.pid file) once their owning process has exited.
#
# Sandboxes live under $TMPDIR, which reboots clear. A sandbox unused for
# several days is reset on its next use (see sandbox_prepare).

set -euo pipefail

# Shared sandbox key contract — see hooks/lib/sandbox.sh.
source "$(dirname "${BASH_SOURCE[0]}")/lib/sandbox.sh"

input=$(cat)
project_dir=$(printf '%s' "$input" | /usr/bin/jq -r '.cwd // ""' 2>/dev/null || true)
[[ -n "$project_dir" && -d "$project_dir" ]] || project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"

SANDBOX_KEY=$(sandbox_key "$project_dir")
if ! [[ "$SANDBOX_KEY" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "[setup-sandbox] Error: invalid sandbox key: $SANDBOX_KEY" >&2
    exit 0
fi

SANDBOX_ROOT="${TMPDIR:-/tmp}/claude-sandbox"
SANDBOX_BASE="$SANDBOX_ROOT/$SANDBOX_KEY"

# --- 1. This worktree's sandbox ---
mkdir -p "$SANDBOX_BASE"
sandbox_prepare "$SANDBOX_BASE"
sandbox_identity "$project_dir" > "$SANDBOX_BASE/worktree"

[[ -d "$SANDBOX_ROOT" ]] || exit 0

# --- 2. Sandboxes of worktrees that no longer exist ---
for peer in "$SANDBOX_ROOT"/wt-*; do
    [[ -d "$peer" && ! -L "$peer" ]] || continue
    [[ "$peer" == "$SANDBOX_BASE" ]] && continue
    # No record yet: a setup may be mid-write. Leave it.
    [[ -f "$peer/worktree" ]] || continue

    owner=""
    IFS= read -r owner < "$peer/worktree" 2>/dev/null || true
    [[ -n "$owner" ]] || continue
    if [[ ! -e "$owner" ]]; then
        rm -rf -- "$peer"
    fi
done

# --- 3. Per-session sandboxes from versions before 0.6.0 ---
# Each holds owner.pid: line 1 the owning process ID, line 2 its `ps -o comm=`
# (to detect a recycled PID). /clear inheritance made some of them symlinks
# to another session's directory. Remove one only when its owner has exited,
# so a session still running an older plugin version keeps its sandbox.
legacy_owner_alive() {
    local pid_file="$1"
    local pid="" comm="" current
    { read -r pid && IFS= read -r comm; } < "$pid_file" 2>/dev/null || true
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    current=$(ps -p "$pid" -o comm= 2>/dev/null || true)
    [[ "$current" == "$comm" ]]
}

for peer in "$SANDBOX_ROOT"/*; do
    name=$(basename "$peer")
    [[ "$name" == wt-* || "$name" == .* ]] && continue

    if [[ -L "$peer" ]]; then
        target=$(readlink "$peer" 2>/dev/null || true)
        if [[ -z "$target" || ! -f "$target/owner.pid" ]] || ! legacy_owner_alive "$target/owner.pid"; then
            # Only the link: `rm -f` never follows it into the target.
            rm -f -- "$peer"
        fi
        continue
    fi

    [[ -d "$peer" ]] || continue
    # Without owner.pid we can't tell who owns it. Leave it to $TMPDIR cleanup.
    [[ -f "$peer/owner.pid" ]] || continue
    if ! legacy_owner_alive "$peer/owner.pid"; then
        rm -rf -- "$peer"
    fi
done

exit 0
