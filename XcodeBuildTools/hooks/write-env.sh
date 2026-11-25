#!/bin/bash
#
# write-env.sh — SessionStart hook (sync)
#
# Populates $CLAUDE_ENV_FILE with the env vars every Bash command needs:
#   - PATH prepended with the plugin's bin/ so wrappers shadow /usr/bin
#   - SANDBOX_DERIVED_DATA / SANDBOX_PACKAGES pointing at this worktree's
#     sandbox base
#
# Runs sync and first in the SessionStart array so the exports are
# available to every subsequent Bash command. setup-sandbox.sh, which
# records the sandbox's worktree and sweeps stale peers, is launched
# through run-background.sh.
#
# The sandbox is keyed per worktree (see hooks/lib/sandbox.sh): a new
# session, a resumed session or a /clear in the same worktree all get the
# same path, so builds stay warm and the absolute paths SPM and Xcode embed
# in their state files stay valid. The ${TMPDIR:-/tmp} prefix is kept
# literal so it expands against the Bash tool context's TMPDIR at command
# time.

set -euo pipefail

# Shared sandbox key contract — see hooks/lib/sandbox.sh.
source "$(dirname "${BASH_SOURCE[0]}")/lib/sandbox.sh"

# CLAUDE_ENV_FILE is the new mechanism; nothing to do if it's absent.
[ -n "${CLAUDE_ENV_FILE:-}" ] || exit 0

input=$(cat)
project_dir=$(printf '%s' "$input" | /usr/bin/jq -r '.cwd // ""' 2>/dev/null || true)
[[ -n "$project_dir" && -d "$project_dir" ]] || project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"

SANDBOX_KEY=$(sandbox_key "$project_dir")

# Validate the shape — defensive, the value is interpolated into
# bash-side strings below.
if ! [[ "$SANDBOX_KEY" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "[write-env] Error: invalid sandbox key: $SANDBOX_KEY" >&2
    exit 0
fi

# --- Write exports ---
# Append (>>) per the docs so we don't clobber other hooks' contributions.

# PATH: ${CLAUDE_PLUGIN_ROOT} is expanded now; $PATH is left literal so
# it expands at source-time in the Bash tool context against whatever
# PATH is in effect there.
echo "export PATH=\"${CLAUDE_PLUGIN_ROOT}/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
echo 'export SANDBOX_DERIVED_DATA="${TMPDIR:-/tmp}/claude-sandbox/'"$SANDBOX_KEY"'/build"'    >> "$CLAUDE_ENV_FILE"
echo 'export SANDBOX_PACKAGES="${TMPDIR:-/tmp}/claude-sandbox/'"$SANDBOX_KEY"'/packages"' >> "$CLAUDE_ENV_FILE"

exit 0
