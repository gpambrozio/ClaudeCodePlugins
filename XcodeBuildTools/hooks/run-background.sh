#!/bin/bash
#
# run-background.sh — Start a hook helper without requiring host-level async support.
#
# Some compatible hosts do not support `async: true` in hooks.json yet. This
# wrapper keeps the hook configuration portable by accepting the hook payload on
# stdin, saving it to a temp file, and launching the real helper in the
# background with stdin restored from that file.
#
# The wrapper's child cannot rely on $PPID for long-lived ownership checks:
# its parent is this short-lived wrapper rather than the host agent process.
# Capture the wrapper's original parent before backgrounding and pass it along
# so helpers can still reason about the owning session process.

set -euo pipefail

relative_target="${1:-}"
if [[ -z "$relative_target" || "$relative_target" == /* || "$relative_target" == *".."* ]]; then
    exit 0
fi

plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
target="$plugin_root/$relative_target"
hook_owner_pid="${CLAUDE_HOOK_OWNER_PID:-$PPID}"

if [[ ! -x "$target" ]]; then
    exit 0
fi

payload_file=$(mktemp "${TMPDIR:-/tmp}/xcodebuildtools-hook.XXXXXX")
cat > "$payload_file"

(
    trap 'rm -f -- "$payload_file"' EXIT
    export CLAUDE_HOOK_OWNER_PID="$hook_owner_pid"
    "$target" < "$payload_file"
) >/dev/null 2>&1 &

exit 0
