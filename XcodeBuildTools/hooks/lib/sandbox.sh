#!/bin/bash
#
# sandbox.sh — Sourceable helpers shared by write-env.sh and setup-sandbox.sh.
#
# Single source of truth for the inheritance-discovery contract. Both
# the sync SessionStart hook (write-env.sh) and the backgrounded
# setup hook (setup-sandbox.sh) need to decide whether the current session is
# inheriting a prior sandbox across /clear — and they must agree on
# *which* anchor. Drift here means write-env.sh embeds one path in
# $CLAUDE_ENV_FILE while setup-sandbox.sh creates a symlink to a
# different one, silently breaking /clear inheritance.
#
# This file is meant to be sourced, not executed. Functions here must:
#   - Not exit (they run inside the caller's shell)
#   - Avoid polluting the caller's namespace (use `local` everywhere)
#   - Communicate results via stdout, never globals
#
# To use:
#     source "$(dirname "${BASH_SOURCE[0]}")/lib/sandbox.sh"

# find_anchor SANDBOX_ROOT TARGET_PID
#
# Echoes the resolved anchor path on stdout if a peer under
# SANDBOX_ROOT is owned by TARGET_PID (owner.pid line 1 match),
# resolving symlinks one hop. Echoes nothing if no match.
#
# Always returns 0 — callers test for an empty result to distinguish
# "no anchor found" from "scan failed".
#
# Eligibility (must all hold):
#   - The peer is a symlink (readable, non-empty target) OR a real dir.
#   - The resolved target is a directory.
#   - $resolved/owner.pid exists and its first line == TARGET_PID.
#
# Note: this intentionally matches setup-sandbox.sh's *inheritance*
# criteria, not its *sweep* criteria. The sweep additionally checks
# owner.pid line 2 (ps comm) for PID-recycling detection; inheritance
# does not currently do that. If we tighten inheritance to require
# comm match, update only this function.
find_anchor() {
    local sandbox_root="$1"
    local target_pid="$2"
    local peer resolved peer_pid

    [[ -d "$sandbox_root" ]] || return 0

    for peer in "$sandbox_root"/*; do
        if [[ -L "$peer" ]]; then
            resolved=$(readlink "$peer" 2>/dev/null) || continue
            [[ -n "$resolved" ]] || continue
        elif [[ -d "$peer" ]]; then
            resolved="$peer"
        else
            continue
        fi

        [[ -d "$resolved" && -f "$resolved/owner.pid" ]] || continue

        peer_pid=""
        { read -r peer_pid; } < "$resolved/owner.pid" 2>/dev/null || continue

        if [[ "$peer_pid" == "$target_pid" ]]; then
            printf '%s\n' "$resolved"
            return 0
        fi
    done

    return 0
}
