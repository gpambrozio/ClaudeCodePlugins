#!/bin/bash
#
# sandbox.sh — Sourceable helpers shared by the sandbox hooks and wrappers.
#
# The build sandbox is keyed per worktree (or per project folder outside
# git), not per session: every session that starts in the same worktree
# gets the same $TMPDIR/claude-sandbox/wt-<name>-<hash>/ directory, so new
# sessions build warm, while separate worktrees keep separate sandboxes.
#
# write-env.sh (sync SessionStart) and setup-sandbox.sh (backgrounded
# SessionStart) must agree on the key; both call sandbox_key here. The
# bin/ wrappers call sandbox_prepare before every build.
#
# This file is meant to be sourced, not executed. Functions here must:
#   - Not exit (they run inside the caller's shell)
#   - Avoid polluting the caller's namespace (use `local` everywhere)
#   - Communicate results via stdout, never globals
#
# To use:
#     source "$(dirname "${BASH_SOURCE[0]}")/lib/sandbox.sh"

# A sandbox untouched for this many days is reset on its next use: macOS
# purges old files under $TMPDIR one by one, and a half-purged DerivedData
# fails in confusing ways, so a clean cold build is the safer outcome.
SANDBOX_STALE_DAYS=3

# sandbox_identity DIRECTORY
#
# Echoes the path that identifies DIRECTORY's worktree: the git dir
# (`git rev-parse --absolute-git-dir`, distinct for every linked worktree and
# shared by its subdirectories), or DIRECTORY's physical path outside git.
sandbox_identity() {
    local directory="$1"
    local git_dir

    git_dir=$(git -C "$directory" rev-parse --absolute-git-dir 2>/dev/null) || git_dir=""
    if [[ -n "$git_dir" ]]; then
        printf '%s\n' "$git_dir"
        return 0
    fi
    (cd "$directory" 2>/dev/null && pwd -P) || printf '%s\n' "$directory"
}

# sandbox_label DIRECTORY
#
# Echoes a short human-readable name for DIRECTORY's checkout (the basename
# of the worktree top level), restricted to [A-Za-z0-9_-].
sandbox_label() {
    local directory="$1"
    local top label

    top=$(git -C "$directory" rev-parse --show-toplevel 2>/dev/null) || top="$directory"
    label=$(printf '%s' "$(basename "$top")" | LC_ALL=C tr -c 'A-Za-z0-9_-' '_' | cut -c1-40)
    printf '%s\n' "${label:-project}"
}

# sha256_hex — sha256 of stdin as lowercase hex, using whichever tool exists.
sha256_hex() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | cut -d' ' -f1
    else
        sha256sum | cut -d' ' -f1
    fi
}

# sandbox_key DIRECTORY
#
# Echoes `wt-<label>-<12 hex digits>`, where the digits hash
# sandbox_identity. Always matches ^[A-Za-z0-9_-]+$.
sandbox_key() {
    local directory="$1"
    local identity label digest

    identity=$(sandbox_identity "$directory")
    label=$(sandbox_label "$directory")
    digest=$(printf '%s' "$identity" | sha256_hex | cut -c1-12)
    printf 'wt-%s-%s\n' "$label" "$digest"
}

# sandbox_base_for BUILD_DIR PACKAGES_DIR
#
# Echoes the per-worktree sandbox base that BUILD_DIR and PACKAGES_DIR belong
# to (…/claude-sandbox/wt-*/{build,packages}). Echoes nothing for any other
# layout, such as the OpenCode entry point's own sandbox, which manages its
# directories itself and must not be touched by sandbox_prepare.
sandbox_base_for() {
    local build_dir="${1%/}" packages_dir="${2%/}"
    local base

    base=$(dirname "$build_dir")
    [[ "$build_dir" == "$base/build" && "$packages_dir" == "$base/packages" ]] || return 0
    [[ "$(basename "$base")" == wt-* && "$(basename "$(dirname "$base")")" == "claude-sandbox" ]] || return 0
    printf '%s\n' "$base"
}

# sandbox_prepare SANDBOX_BASE
#
# Makes sure SANDBOX_BASE/build and SANDBOX_BASE/packages exist and records
# the use. If the sandbox has not been used for SANDBOX_STALE_DAYS, its
# contents are moved aside and deleted in the background first. Safe to call
# before every build: a stale sandbox has had no build for days, so nothing
# is writing to it.
sandbox_prepare() {
    local base="$1"
    local marker="$base/.last-used"
    local stale=0 trash entry

    if [[ -f "$marker" ]]; then
        if [[ -n "$(find "$marker" -mtime +$((SANDBOX_STALE_DAYS - 1)) 2>/dev/null)" ]]; then
            stale=1
        fi
    elif [[ -d "$base/build" || -d "$base/packages" ]]; then
        # Contents without a marker: the marker itself was purged.
        stale=1
    fi

    if [[ $stale -eq 1 ]]; then
        trash=$(mktemp -d "$base/.stale.XXXXXX" 2>/dev/null) || trash=""
        if [[ -n "$trash" ]]; then
            for entry in build packages; do
                if [[ -e "$base/$entry" ]]; then
                    mv -- "$base/$entry" "$trash/" 2>/dev/null || true
                fi
            done
            (/bin/rm -rf -- "$trash" >/dev/null 2>&1 &)
        fi
    fi

    # Marker first: anyone who sees build/ must also see the marker, or a
    # concurrent call would take the new sandbox for a purged one.
    mkdir -p "$base" 2>/dev/null || true
    touch "$marker" 2>/dev/null || true
    mkdir -p "$base/build" "$base/packages" 2>/dev/null || true
    return 0
}
