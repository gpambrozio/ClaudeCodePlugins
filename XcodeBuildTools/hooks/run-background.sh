#!/bin/bash
#
# run-background.sh — Start a hook helper without requiring host-level async support.
#
# Some compatible hosts do not support `async: true` in hooks.json yet. This
# wrapper keeps the hook configuration portable by accepting the hook payload on
# stdin, saving it to a temp file, and launching the real helper in the
# background with stdin restored from that file.

set -euo pipefail

relative_target="${1:-}"
if [[ -z "$relative_target" || "$relative_target" == /* || "$relative_target" == *".."* ]]; then
    exit 0
fi

plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
target="$plugin_root/$relative_target"

if [[ ! -x "$target" ]]; then
    exit 0
fi

payload_file=$(mktemp "${TMPDIR:-/tmp}/xcodebuildtools-hook.XXXXXX")
cat > "$payload_file"

(
    trap 'rm -f -- "$payload_file"' EXIT
    "$target" < "$payload_file"
) >/dev/null 2>&1 &

exit 0
