#!/bin/bash

# Output the session start instructions as additionalContext
# Reading content from session-start.md file

MD_FILE="$(dirname "$0")/session-start.md"

# Exit silently if the markdown file doesn't exist
if [ ! -f "$MD_FILE" ]; then
    exit 0
fi

# Read the file and escape it properly for JSON using jq
ADDITIONAL_CONTEXT=$(cat "$MD_FILE" | jq -Rs .)

# Output the JSON structure with the content from the markdown file
cat << EOF
{
  "systemMessage": "The SwiftDevelopment plugin is loaded and ready to help with Swift and iOS development tasks.",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": $ADDITIONAL_CONTEXT
  }
}
EOF

exit 0
