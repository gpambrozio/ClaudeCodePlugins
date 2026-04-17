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
# (teardown-sandbox.sh) handles explicit cleanup.

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

# --- Create sandbox directories ---
SANDBOX_BASE="${TMPDIR:-/tmp}/claude-sandbox/$SESSION_ID"
mkdir -p "$SANDBOX_BASE/build" "$SANDBOX_BASE/packages"
