#!/bin/bash
#
# write-env.sh — SessionStart hook (sync)
#
# Populates $CLAUDE_ENV_FILE with the env vars every Bash command needs:
#   - PATH prepended with the plugin's bin/ so wrappers shadow /usr/bin
#   - SANDBOX_DERIVED_DATA / SANDBOX_PACKAGES pointing at this session's
#     sandbox base
#
# Runs SYNC and FIRST in the SessionStart array so the exports are
# available to every subsequent Bash command. setup-sandbox.sh, which
# does the slower dir-creation + peer sweep, keeps running async.
#
# Anchor detection: on /clear the prior session's sandbox dir is owned
# by our $PPID (the host agent is the same process). We scan SANDBOX_ROOT peers
# the same way setup-sandbox.sh does and, if we find one, embed the
# anchor's real path into the env vars — SPM and Xcode persist absolute
# paths into state files, so handing them the symlink path would break
# rebuilds once the symlink is later swept. For a truly fresh session,
# we defer to bash-side ${TMPDIR:-/tmp} expansion at command time.

set -euo pipefail

# Shared inheritance-discovery contract — see hooks/lib/sandbox.sh.
source "$(dirname "${BASH_SOURCE[0]}")/lib/sandbox.sh"

# CLAUDE_ENV_FILE is the new mechanism; nothing to do if it's absent.
[ -n "${CLAUDE_ENV_FILE:-}" ] || exit 0

input=$(cat)
SESSION_ID=$(printf '%s' "$input" | /usr/bin/jq -r '.session_id // ""')

# Validate the shape — defensive, the value is interpolated into
# bash-side strings further down.
if ! [[ "$SESSION_ID" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "[write-env] Error: invalid session_id: $SESSION_ID" >&2
    exit 0
fi

SANDBOX_ROOT="${TMPDIR:-/tmp}/claude-sandbox"

# --- Anchor detection ---
# On /clear, the host agent is the same process — any peer owned by $PPID is
# the prior session's sandbox we want to inherit.
anchor=$(find_anchor "$SANDBOX_ROOT" "$PPID")

# --- Write exports ---
# Append (>>) per the docs so we don't clobber other hooks' contributions.

# PATH: ${CLAUDE_PLUGIN_ROOT} is expanded now; $PATH is left literal so
# it expands at source-time in the Bash tool context against whatever
# PATH is in effect there.
echo "export PATH=\"${CLAUDE_PLUGIN_ROOT}/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"

if [[ -n "$anchor" ]]; then
    # Inherited sandbox: embed the anchor's real absolute path so SPM
    # and Xcode state files stay valid even after the per-session
    # symlink is swept by a future setup-sandbox.sh pass. %q handles
    # the unlikely case of shell-special chars in $TMPDIR.
    printf 'export SANDBOX_DERIVED_DATA=%q\n' "$anchor/build"    >> "$CLAUDE_ENV_FILE"
    printf 'export SANDBOX_PACKAGES=%q\n'    "$anchor/packages" >> "$CLAUDE_ENV_FILE"
else
    # Fresh sandbox: keep ${TMPDIR:-/tmp} literal so the Bash tool
    # context's TMPDIR applies at command time. SESSION_ID is validated
    # against [A-Za-z0-9_-]+ above so embedding it is safe.
    echo 'export SANDBOX_DERIVED_DATA="${TMPDIR:-/tmp}/claude-sandbox/'"$SESSION_ID"'/build"'    >> "$CLAUDE_ENV_FILE"
    echo 'export SANDBOX_PACKAGES="${TMPDIR:-/tmp}/claude-sandbox/'"$SESSION_ID"'/packages"' >> "$CLAUDE_ENV_FILE"
fi

exit 0
