#!/bin/bash
#
# teardown-sandbox.sh — Remove isolated Xcode build environment on session stop
#
# Cleans up the per-session sandbox created by setup-sandbox.sh:
#   - ${TMPDIR}/claude-sandbox/$PPID/  (build, packages, bin directories)
#   - ${TMPDIR}/claude-sandbox-$PPID   (path pointer file)
#
# Runs as a Stop hook.

set -euo pipefail

SESSION_PID="${PPID:-$$}"
SANDBOX_ROOT="${TMPDIR:-/tmp}/claude-sandbox"
SANDBOX_BASE="$SANDBOX_ROOT/$SESSION_PID"
PATH_FILE="${TMPDIR:-/tmp}/claude-sandbox-$SESSION_PID"

# Remove session sandbox directory
if [[ -d "$SANDBOX_BASE" ]]; then
    rm -rf "$SANDBOX_BASE"
fi

# Remove path pointer file
if [[ -f "$PATH_FILE" ]]; then
    rm -f "$PATH_FILE"
fi
