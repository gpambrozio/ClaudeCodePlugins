#!/bin/bash
# approve-xcode-mcp.sh
# Auto-clicks "Allow" on Xcode's windowed MCP agent authorization dialog.
#
# Windowed mode only. Xcode 27's headless MCP server has no dialog to click:
# its approvals are made by the owner with
# `sudo xcrun mcp-server approve <id>` and `allow-folder <path>`. This helper
# clicks only when windowed mode is positively established: Xcode 26.x (no
# `mcp-server` tool at all), or Xcode 27 whose status probe answers within a
# few seconds and reports permission.enabled as the JSON boolean false. A
# failed, stalled or unreadable probe, or any other value, leaves it idle.
#
# Started through run-background.sh so it doesn't block startup.
#   1. Pre-checks: Xcode must be running, mcpbridge must exist, and windowed
#      mode must be established as above
#   2. Checks Accessibility permissions (notifies + opens Settings if missing)
#   3. Polls Xcode's windows for the auth dialog (up to 15 seconds)
#   4. Clicks "Allow" when found, or exits silently on timeout
#
# Prerequisite (one-time):
#   System Settings > Privacy & Security > Accessibility
#   → Add your terminal app (Terminal.app, iTerm2, etc.)

# --- Pre-checks: bail early if Xcode or mcpbridge aren't available ---
if ! pgrep -x Xcode &>/dev/null; then
    exit 0
fi

if ! xcrun --find mcpbridge &>/dev/null; then
    exit 0
fi

# --- Headless mode (Xcode 27+): approvals happen through sudo, never a click ---
STATUS_TIMEOUT="${XCODEBUILDTOOLS_MCP_STATUS_TIMEOUT:-5}"
[[ "$STATUS_TIMEOUT" =~ ^[0-9]+$ && "$STATUS_TIMEOUT" -gt 0 ]] || STATUS_TIMEOUT=5

# Run a command with stdout in a file (so a stalled grandchild can't hold a
# pipe open), killing its whole process group after $1 seconds. Prints the
# output on success.
run_bounded() {
    local seconds="$1"
    shift
    local output pid ticks=0 status=0
    output=$(mktemp "${TMPDIR:-/tmp}/approve-xcode-mcp.XXXXXX") || return 1
    # Job control puts the background job in its own process group (its
    # PGID is $pid), so a timeout can kill the probe's children too.
    set -m
    "$@" >"$output" 2>/dev/null </dev/null &
    pid=$!
    set +m
    while kill -0 "$pid" 2>/dev/null; do
        if (( ticks >= seconds * 10 )); then
            kill -9 -- "-$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
            rm -f "$output"
            return 124
        fi
        sleep 0.1
        ticks=$((ticks + 1))
    done
    wait "$pid" || status=$?
    [[ $status -eq 0 ]] && cat "$output"
    rm -f "$output"
    return "$status"
}

# `xcrun mcp-server` ships with Xcode 27. Without it this is Xcode 26.x,
# which is windowed only.
if xcrun --find mcp-server &>/dev/null; then
    status_json=$(run_bounded "$STATUS_TIMEOUT" xcrun mcp-server status --format json) || exit 0
    # Only a JSON boolean counts: a missing, null or string value is unknown.
    headless_enabled=$(printf '%s' "$status_json" | /usr/bin/jq -r \
        '.permission.enabled | if type == "boolean" then tostring else "unknown" end' 2>/dev/null || true)
    if [[ "$headless_enabled" != "false" ]]; then
        exit 0
    fi
fi

# --- Check Accessibility permissions ---
if ! osascript -e 'tell application "System Events" to get name of first process' &>/dev/null; then
    osascript -e '
        display notification "Grant Accessibility access to your terminal app in System Settings → Privacy & Security → Accessibility" ¬
            with title "Xcode MCP Auto-Approve" ¬
            subtitle "Missing Accessibility permissions"
    '
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    exit 0
fi

# --- Give MCP bridge time to connect and trigger the dialog ---
sleep 2

# --- Poll for up to 15s for the MCP auth dialog and click Allow ---
osascript <<'APPLESCRIPT' >/dev/null 2>&1
tell application "System Events"
    tell process "Xcode"
        repeat 15 times
            repeat with xcodeWindow in windows
                try
                    repeat with dialogText in static texts of xcodeWindow
                        if value of dialogText contains "access Xcode" then
                            click button "Allow" of xcodeWindow
                            return "approved"
                        end if
                    end repeat
                end try
                try
                    repeat with sheetText in static texts of sheet 1 of xcodeWindow
                        if value of sheetText contains "access Xcode" then
                            click button "Allow" of sheet 1 of xcodeWindow
                            return "approved"
                        end if
                    end repeat
                end try
            end repeat
            delay 1
        end repeat
    end tell
end tell
return "timeout"
APPLESCRIPT

# Silent exit regardless of result — no notification spam
exit 0
