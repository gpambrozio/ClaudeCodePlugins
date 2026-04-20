#!/bin/bash
#
# setup-sandbox.sh — Create isolated Xcode build environment (per-session)
#
# Creates per-session sandbox directories for DerivedData and SPM cache,
# isolating CLI builds from Xcode's own storage. The wrapper scripts in
# bin/ (xcodebuild-sandbox, swift-sandbox) read $CLAUDE_SESSION_ID at
# runtime and inject the appropriate isolation flags.
#
# Each Claude Code session gets its own sandbox keyed by the session ID
# from the SessionStart hook's stdin payload. The same ID is propagated
# into Bash tool invocations by hooks/inject-session-id.py, which makes
# it stable across contexts (unlike $PPID).
#
# The sandbox lives under $TMPDIR so it auto-cleans on reboot; macOS
# also purges $TMPDIR entries untouched for 3+ days. The SessionEnd hook
# (teardown-sandbox.sh) handles explicit cleanup. As a safety net for
# sessions that exit without firing SessionEnd (crashes, force-quit),
# this script also sweeps peer sandbox directories whose owner PID is
# dead or has been recycled to a different process.

set -euo pipefail

# --- Read session_id from hook stdin payload ---
input=$(cat)
SESSION_ID=$(printf '%s' "$input" | /usr/bin/python3 -c \
    'import sys,json; print(json.load(sys.stdin).get("session_id",""))')

if [[ -z "$SESSION_ID" ]]; then
    echo "[setup-sandbox] Error: no session_id in hook payload" >&2
    exit 0
fi

# Validate session ID shape — defensive, protects downstream rm -rf
if ! [[ "$SESSION_ID" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "[setup-sandbox] Error: invalid session_id: $SESSION_ID" >&2
    exit 0
fi

SANDBOX_ROOT="${TMPDIR:-/tmp}/claude-sandbox"
SANDBOX_BASE="$SANDBOX_ROOT/$SESSION_ID"

# --- Create sandbox dirs and claim with an owner PID marker ---
# The hook is marked async in hooks.json so Claude doesn't wait for the
# peer sweep; creating build/packages and writing owner.pid *before* the
# sweep guarantees the wrappers find everything they need even if a Bash
# tool fires while the sweep is still running. Writing owner.pid before
# the sweep also closes the window where a racing sibling setup could
# see our dir without a marker and treat it as abandoned. $PPID in a
# SessionStart hook is Claude itself (no intermediate shell — that was
# the Bash-tool context's problem, not ours).
# Line 1: PID. Line 2: `ps -o comm=` output for PID-recycling detection.
mkdir -p "$SANDBOX_BASE/build" "$SANDBOX_BASE/packages"
{
    printf '%s\n' "$PPID"
    ps -p "$PPID" -o comm= 2>/dev/null || true
} > "$SANDBOX_BASE/owner.pid"

# --- Sweep stale peer sandboxes (dead or recycled owner PIDs) ---
# Peers without an owner.pid are skipped — either legacy dirs from
# before this change or a racing setup mid-write. macOS' 3-day $TMPDIR
# purge collects them eventually.
if [[ -d "$SANDBOX_ROOT" ]]; then
    for peer in "$SANDBOX_ROOT"/*; do
        [[ -d "$peer" ]] || continue
        [[ "$peer" == "$SANDBOX_BASE" ]] && continue

        peer_pid_file="$peer/owner.pid"
        [[ -f "$peer_pid_file" ]] || continue

        peer_pid=""
        peer_comm=""
        { read -r peer_pid && IFS= read -r peer_comm; } \
            < "$peer_pid_file" 2>/dev/null || continue
        [[ "$peer_pid" =~ ^[0-9]+$ ]] || continue

        # Dead PID → sweep.
        if ! kill -0 "$peer_pid" 2>/dev/null; then
            rm -rf -- "$peer"
            continue
        fi

        # Live PID but recycled to a different process → sweep.
        current_comm=$(ps -p "$peer_pid" -o comm= 2>/dev/null || true)
        if [[ "$current_comm" != "$peer_comm" ]]; then
            rm -rf -- "$peer"
        fi
    done
fi
