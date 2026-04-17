#!/bin/bash
#
# teardown-sandbox.sh — Remove isolated Xcode build environment on session end
#
# Reads session_id from the SessionEnd hook stdin payload and removes the
# matching $TMPDIR/claude-sandbox/<session_id>/ directory created by
# setup-sandbox.sh.

set -euo pipefail

input=$(cat)
SESSION_ID=$(printf '%s' "$input" | /usr/bin/python3 -c \
    'import sys,json; print(json.load(sys.stdin).get("session_id",""))')

if [[ -z "$SESSION_ID" ]]; then
    exit 0
fi

# Validate session ID shape before using it in a path for rm -rf
if ! [[ "$SESSION_ID" =~ ^[A-Za-z0-9_-]+$ ]]; then
    exit 0
fi

SANDBOX_BASE="${TMPDIR:-/tmp}/claude-sandbox/$SESSION_ID"
if [[ -d "$SANDBOX_BASE" ]]; then
    rm -rf "$SANDBOX_BASE"
fi
