#!/bin/bash
#
# setup-sandbox.sh — Create isolated Xcode build environment (per-session)
#
# Creates per-session sandbox directories for DerivedData and SPM cache,
# isolating CLI builds from Xcode's own storage. The wrapper scripts in
# bin/ (xcodebuild, swift) read $SANDBOX_DERIVED_DATA and $SANDBOX_PACKAGES
# at runtime and inject the appropriate isolation flags; those env vars
# are set on every Bash tool command by hooks/inject-session-id.py from
# the hook payload's session_id (stable across contexts unlike $PPID).
#
# Each Claude Code session gets its own sandbox keyed by the session ID
# from the SessionStart hook's stdin payload.
#
# The sandbox lives under $TMPDIR so it auto-cleans on reboot; macOS
# also purges $TMPDIR entries untouched for 3+ days. The SessionEnd hook
# (teardown-sandbox.py) handles explicit cleanup for logout/exit reasons
# but is skipped for /clear — on /clear, Claude Code keeps running
# (same $PPID) and just resets conversation state, so this script
# inherits the prior session's sandbox rather than creating a fresh one.
#
# Inheritance is via **symlink**, not rename. State files under the
# sandbox (SPM's workspace-state.json, Xcode's CompilationCache and
# ModuleCache) embed absolute paths to their own extraction/cache
# directories. Renaming the sandbox dir to the new session_id changed
# the path on disk but left those embedded paths pointing at the old
# session_id — breaking subsequent builds of binary SPM targets
# (Sparkle.xcframework and friends) and explicit-module caches, which
# is why users had to nuke DerivedData after each /clear. By symlinking
# the new session's sandbox path to the original anchor directory, the
# anchor's path stays stable on disk and every embedded absolute path
# continues to resolve.
#
# As a safety net for sessions that exit without firing SessionEnd
# (crashes, force-quit), this script also sweeps peer sandbox entries
# whose owner PID is dead or has been recycled to a different process.
# The sweep is symlink-aware: dangling symlinks and symlinks owned by
# dead processes are removed (the symlink only, never the target via
# rm -rf), and real dirs are only removed when no live symlink still
# references them.

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

# Resolve a symlink one level to its absolute target. macOS' default
# `readlink` returns the raw link text; since we always write absolute
# paths via `ln -s`, one hop is enough. Empty output on any failure.
resolve_link() {
    local target
    target=$(readlink "$1" 2>/dev/null) || return 1
    [[ -n "$target" ]] || return 1
    printf '%s\n' "$target"
}

# --- Inherit prior session's sandbox on /clear (via symlink) ---
# $PPID in a SessionStart hook is Claude itself (no intermediate shell
# — that was the Bash-tool context's problem, not ours). After /clear,
# Claude is the same process, so any peer whose resolved owner.pid
# matches our PID belongs to us. Inherit it by creating $SANDBOX_BASE
# as a symlink to the anchor, preserving embedded absolute paths.
anchor=""
if [[ -d "$SANDBOX_ROOT" ]]; then
    for peer in "$SANDBOX_ROOT"/*; do
        # Follow symlinks to the underlying anchor dir; real dirs are
        # their own anchor. Anything else (missing, not a dir) skipped.
        if [[ -L "$peer" ]]; then
            resolved=$(resolve_link "$peer") || continue
        elif [[ -d "$peer" ]]; then
            resolved="$peer"
        else
            continue
        fi
        [[ -d "$resolved" ]] || continue
        [[ -f "$resolved/owner.pid" ]] || continue

        peer_pid=""
        { read -r peer_pid; } < "$resolved/owner.pid" 2>/dev/null || continue
        if [[ "$peer_pid" == "$PPID" ]]; then
            anchor="$resolved"
            break
        fi
    done
fi

inherited=0
if [[ -n "$anchor" && "$anchor" != "$SANDBOX_BASE" ]]; then
    # session_ids are unique, but a leftover entry at $SANDBOX_BASE
    # would block `ln -s`. Remove it in the way that matches its type.
    if [[ -L "$SANDBOX_BASE" ]]; then
        rm -f -- "$SANDBOX_BASE"
    elif [[ -e "$SANDBOX_BASE" ]]; then
        rm -rf -- "$SANDBOX_BASE"
    fi
    mkdir -p "$SANDBOX_ROOT"
    ln -s "$anchor" "$SANDBOX_BASE"
    inherited=1
fi

# --- Ensure sandbox dirs and owner.pid marker are in place ---
# For a fresh sandbox, create build/packages and stamp owner.pid before
# the peer sweep so concurrent wrappers (Bash tool is async) find
# everything, and so the sweep doesn't see us as abandoned. For an
# inherited (symlinked) sandbox, the anchor already has all of this —
# touching it again would re-stamp owner.pid for no reason.
# Line 1: PID. Line 2: `ps -o comm=` output for PID-recycling detection.
if [[ $inherited -eq 0 ]]; then
    mkdir -p "$SANDBOX_BASE/build" "$SANDBOX_BASE/packages"
    {
        printf '%s\n' "$PPID"
        ps -p "$PPID" -o comm= 2>/dev/null || true
    } > "$SANDBOX_BASE/owner.pid"
fi

# --- Sweep stale peer sandboxes ---
# Two passes: symlinks first, real dirs second. Doing symlinks first
# means real-dir decisions can trust the current set of live symlinks;
# otherwise we'd race our own cleanup. Real-dir removals additionally
# skip any dir still targeted by a live symlink (defensive — this
# shouldn't happen in practice since an anchor's only references are
# from the same session that owns it).
#
# rm usage:
#   - `rm -f "$link"` for symlinks (no -r; `rm -rf symlink/` with a
#     trailing slash would wipe the target contents).
#   - `rm -rf "$dir"` for real dirs.
if [[ -d "$SANDBOX_ROOT" ]]; then
    # Pass 1: symlinks
    for peer in "$SANDBOX_ROOT"/*; do
        [[ -L "$peer" ]] || continue
        [[ "$peer" == "$SANDBOX_BASE" ]] && continue

        target=$(resolve_link "$peer") || target=""

        # Dangling or non-dir target → orphan symlink.
        if [[ -z "$target" || ! -d "$target" ]]; then
            rm -f -- "$peer"
            continue
        fi

        peer_pid_file="$target/owner.pid"
        if [[ ! -f "$peer_pid_file" ]]; then
            rm -f -- "$peer"
            continue
        fi

        peer_pid=""
        peer_comm=""
        { read -r peer_pid && IFS= read -r peer_comm; } \
            < "$peer_pid_file" 2>/dev/null || continue
        if ! [[ "$peer_pid" =~ ^[0-9]+$ ]]; then
            rm -f -- "$peer"
            continue
        fi

        # Owned by *us* but isn't our current sandbox — leftover from
        # a prior /clear in this same process. Drop just the symlink.
        if [[ "$peer_pid" == "$PPID" ]]; then
            rm -f -- "$peer"
            continue
        fi

        # Dead PID → orphan symlink.
        if ! kill -0 "$peer_pid" 2>/dev/null; then
            rm -f -- "$peer"
            continue
        fi

        # Live PID but recycled to a different process → orphan.
        current_comm=$(ps -p "$peer_pid" -o comm= 2>/dev/null || true)
        if [[ "$current_comm" != "$peer_comm" ]]; then
            rm -f -- "$peer"
        fi
    done

    # Pass 2: real directories
    for peer in "$SANDBOX_ROOT"/*; do
        # Skip symlinks (handled above) and non-dirs.
        [[ -L "$peer" ]] && continue
        [[ -d "$peer" ]] || continue
        [[ "$peer" == "$SANDBOX_BASE" ]] && continue

        peer_pid_file="$peer/owner.pid"
        # Peers without owner.pid are either legacy dirs from before
        # this infrastructure or a racing setup mid-write — leave them.
        [[ -f "$peer_pid_file" ]] || continue

        peer_pid=""
        peer_comm=""
        { read -r peer_pid && IFS= read -r peer_comm; } \
            < "$peer_pid_file" 2>/dev/null || continue
        [[ "$peer_pid" =~ ^[0-9]+$ ]] || continue

        # Defensive: if any live symlink in SANDBOX_ROOT still points
        # at this dir, it's still in use. Skip removal this pass.
        still_referenced=0
        for candidate in "$SANDBOX_ROOT"/*; do
            [[ -L "$candidate" ]] || continue
            candidate_target=$(resolve_link "$candidate") || continue
            if [[ "$candidate_target" == "$peer" ]]; then
                still_referenced=1
                break
            fi
        done
        [[ $still_referenced -eq 1 ]] && continue

        # Dead PID → sweep.
        if ! kill -0 "$peer_pid" 2>/dev/null; then
            rm -rf -- "$peer"
            continue
        fi

        # Owned by us but isn't our current sandbox — shouldn't happen
        # in the symlink model (we create symlinks, not dirs, on
        # inherit) but could appear if a legacy session left this
        # behind. Drop it.
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
