#!/bin/bash
#
# setup-sandbox.sh — Create isolated Xcode build environment (per-session)
#
# Creates per-session sandbox directories for DerivedData and SPM cache,
# isolating CLI builds from Xcode's own storage. The wrapper scripts in
# bin/ (xcodebuild, swift) read $CLAUDE_SESSION_ID at runtime and inject
# the appropriate isolation flags.
#
# Each Claude Code session gets its own sandbox keyed by the session ID
# from the SessionStart hook's stdin payload. The same ID is propagated
# into Bash tool invocations by hooks/inject-session-id.py, which makes
# it stable across contexts (unlike $PPID).
#
# The sandbox lives under $TMPDIR so it auto-cleans on reboot; macOS
# also purges $TMPDIR entries untouched for 3+ days. The SessionEnd hook
# (teardown-sandbox.py) handles explicit cleanup for logout/exit reasons
# but is skipped for /clear — on /clear, Claude Code keeps running
# (same $PPID) and just resets conversation state, so this script
# inherits the prior session's sandbox by renaming it to the new
# session_id rather than creating a fresh one.
#
# As a safety net for sessions that exit without firing SessionEnd
# (crashes, force-quit), this script also sweeps peer sandbox
# directories whose owner PID is dead or has been recycled to a
# different process.

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

# --- Inherit prior session's sandbox on /clear ---
# $PPID in a SessionStart hook is Claude itself (no intermediate shell
# — that was the Bash-tool context's problem, not ours). After /clear,
# Claude is the same process, so any peer dir whose owner.pid matches
# our PID belongs to us and should be renamed to the new session_id
# instead of being recreated. Same-filesystem mv is O(1).
existing=""
if [[ -d "$SANDBOX_ROOT" ]]; then
    for peer in "$SANDBOX_ROOT"/*; do
        [[ -d "$peer" ]] || continue
        [[ -f "$peer/owner.pid" ]] || continue
        peer_pid=""
        { read -r peer_pid; } < "$peer/owner.pid" 2>/dev/null || continue
        if [[ "$peer_pid" == "$PPID" ]]; then
            existing="$peer"
            break
        fi
    done
fi

if [[ -n "$existing" && "$existing" != "$SANDBOX_BASE" ]]; then
    # Target shouldn't exist (session_ids are unique), but be defensive.
    [[ -e "$SANDBOX_BASE" ]] && rm -rf -- "$SANDBOX_BASE"
    mv "$existing" "$SANDBOX_BASE"
fi

# --- Ensure sandbox dirs and owner.pid marker are in place ---
# The hook is marked async in hooks.json so Claude doesn't wait for the
# peer sweep; creating build/packages and writing owner.pid *before* the
# sweep guarantees the wrappers find everything they need even if a Bash
# tool fires while the sweep is still running. The marker also closes
# the window where a racing sibling setup could see our dir without
# owner.pid and treat it as abandoned.
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

        # Owned by *us* but isn't our current sandbox — duplicate left
        # over from an earlier /clear whose rename never completed.
        if [[ "$peer_pid" == "$PPID" ]]; then
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
