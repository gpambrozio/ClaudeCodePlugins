#!/bin/bash
#
# setup-sandbox.sh — Create isolated Xcode build environment (per-session)
#
# Creates wrapper scripts for xcodebuild and swift that transparently inject
# -derivedDataPath / -clonedSourcePackagesDirPath / --cache-path flags,
# isolating CLI builds from Xcode's own DerivedData and SPM cache.
#
# Each Claude Code session gets its own sandbox keyed by PPID (the Claude
# process PID). Multiple sessions can build concurrently without conflicts.
#
# The sandbox lives inside Xcode's DerivedData directory so that nuking
# DerivedData also cleans up all sandbox state — matching developer expectations.
#
# Runs as a SessionStart hook; outputs JSON for Claude Code.

set -euo pipefail

# --- Locate Xcode's DerivedData ---
# Respect custom DerivedData location if the developer configured one.
CUSTOM_DD=$(defaults read com.apple.dt.Xcode IDECustomDerivedDataLocation 2>/dev/null || echo "")
if [[ -n "$CUSTOM_DD" ]]; then
    DERIVED_DATA="$CUSTOM_DD"
else
    DERIVED_DATA="$HOME/Library/Developer/Xcode/DerivedData"
fi

# --- Per-session sandbox paths ---
SESSION_PID="${PPID:-$$}"
SANDBOX_ROOT="$DERIVED_DATA/claude-sandbox"
SANDBOX_BASE="$SANDBOX_ROOT/$SESSION_PID"
SANDBOX_BUILD="$SANDBOX_BASE/build"
SANDBOX_PKGS="$SANDBOX_BASE/packages"
SANDBOX_BIN="$SANDBOX_BASE/bin"

# --- Clean up stale sessions ---
# Iterate all PID dirs under claude-sandbox/. If the owning process is dead
# (or the PID was reused by a non-Claude process), remove that session's sandbox.
if [[ -d "$SANDBOX_ROOT" ]]; then
    for session_dir in "$SANDBOX_ROOT"/*/; do
        [[ -d "$session_dir" ]] || continue
        pid=$(basename "$session_dir")
        # Skip non-numeric directory names
        [[ "$pid" =~ ^[0-9]+$ ]] || continue
        # Skip our own session
        [[ "$pid" == "$SESSION_PID" ]] && continue

        is_alive=false
        if kill -0 "$pid" 2>/dev/null; then
            pid_cmd=$(ps -o command= -p "$pid" 2>/dev/null || echo "")
            if [[ "$pid_cmd" == *claude* || "$pid_cmd" == *node* ]]; then
                is_alive=true
            fi
        fi

        if [[ "$is_alive" == "false" ]]; then
            rm -rf "$session_dir"
            rm -f "/tmp/claude-sandbox-$pid"
        fi
    done
fi

# --- Create sandbox directories ---
mkdir -p "$SANDBOX_BUILD" "$SANDBOX_PKGS" "$SANDBOX_BIN"

# --- Write path file for skill file discovery ---
# Skill files use $(cat /tmp/claude-sandbox-$(echo $PPID)) to find the sandbox.
# This indirection lets the hook respect custom DerivedData locations while
# keeping skill file paths stable.
echo "$SANDBOX_BASE" > "/tmp/claude-sandbox-$SESSION_PID"

# --- APFS clone system SPM cache if sandbox packages dir is empty ---
# cp -c creates instant copy-on-write clones on APFS: zero extra disk until
# writes diverge. Falls back to regular copy on non-APFS volumes.
if [[ -z "$(ls -A "$SANDBOX_PKGS" 2>/dev/null)" ]]; then
    system_spm="$HOME/Library/Caches/org.swift.swiftpm"
    if [[ -d "$system_spm" ]]; then
        cp -cpR "$system_spm/" "$SANDBOX_PKGS/" 2>/dev/null || true
    fi
fi

# --- Create xcodebuild wrapper ---
# Injects -derivedDataPath and -clonedSourcePackagesDirPath so CLI builds
# use isolated storage instead of Xcode's default DerivedData.
cat > "$SANDBOX_BIN/xcodebuild" << WRAPPER
#!/bin/bash
exec /usr/bin/xcodebuild \\
    -derivedDataPath "$SANDBOX_BUILD" \\
    -clonedSourcePackagesDirPath "$SANDBOX_PKGS" \\
    "\$@"
WRAPPER
chmod +x "$SANDBOX_BIN/xcodebuild"

# --- Create swift wrapper (subcommand-aware) ---
# Only injects --cache-path for subcommands that accept SwiftPM flags
# (build, test, run). Other subcommands (package, repl, --version) pass through.
cat > "$SANDBOX_BIN/swift" << WRAPPER
#!/bin/bash
case "\${1:-}" in
    build|test|run)
        exec /usr/bin/swift "\$@" \\
            --cache-path "$SANDBOX_PKGS"
        ;;
    *)
        exec /usr/bin/swift "\$@"
        ;;
esac
WRAPPER
chmod +x "$SANDBOX_BIN/swift"

# --- Output hook response ---
printf '{"systemMessage":""}\n'
