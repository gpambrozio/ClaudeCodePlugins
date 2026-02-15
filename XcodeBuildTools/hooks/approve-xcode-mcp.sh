#!/bin/bash
# approve-xcode-mcp.sh
# Auto-clicks "Allow" on Xcode's MCP agent authorization dialog.
#
# Runs as an async hook (async: true in hooks.json) so it doesn't block startup.
#   1. Pre-checks: Xcode must be running and mcpbridge must exist
#   2. Lock file prevents redundant runs for the same Xcode instance
#   3. Checks Accessibility permissions (notifies + opens Settings if missing)
#   4. Polls Xcode's windows for the auth dialog (up to 10 seconds)
#   5. Clicks "Allow" when found, or exits silently on timeout
#
# Prerequisite (one-time):
#   System Settings > Privacy & Security > Accessibility
#   → Add your terminal app (Terminal.app, iTerm2, etc.)

# --- Pre-checks: bail early if Xcode or mcpbridge aren't available ---
XCODE_PID=$(pgrep -x Xcode 2>/dev/null)
if [[ -z "$XCODE_PID" ]]; then
    exit 0
fi

if ! xcrun --find mcpbridge &>/dev/null; then
    exit 0
fi

# --- Lock file keyed on Xcode PID (prevents re-runs for same instance) ---
LOCK_FILE="${TMPDIR:-/tmp}/xcode-mcp-approve-${XCODE_PID}.lock"
if [[ -f "$LOCK_FILE" ]]; then
    exit 0
fi
touch "$LOCK_FILE"

# --- Check Accessibility permissions ---
if ! osascript -e 'tell application "System Events" to get name of first process' &>/dev/null; then
    osascript -e '
        display notification "Grant Accessibility access to your terminal app in System Settings → Privacy & Security → Accessibility" ¬
            with title "Xcode MCP Auto-Approve" ¬
            subtitle "Missing Accessibility permissions"
    '
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    rm -f "$LOCK_FILE"
    exit 0
fi

# --- Give MCP bridge time to connect and trigger the dialog ---
sleep 2

# --- Poll for up to 10s for the MCP auth dialog and click Allow ---
osascript <<'APPLESCRIPT' >/dev/null 2>&1
tell application "System Events"
    tell process "Xcode"
        repeat 10 times
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
