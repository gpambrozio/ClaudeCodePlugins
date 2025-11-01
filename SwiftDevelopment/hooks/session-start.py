#!/usr/bin/env python3

import sys
import json
import os

def main():
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        md_file = os.path.join(script_dir, "session-start.md")

        # Exit silently if the markdown file doesn't exist
        if not os.path.exists(md_file):
            sys.exit(0)

        # Read the markdown file
        with open(md_file, 'r', encoding='utf-8') as f:
            additional_context = f.read()

        # Output the JSON structure with the content from the markdown file
        response = {
            "systemMessage": "The SwiftDevelopment plugin is loaded and ready to help with Swift and iOS development tasks.",
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": additional_context
            }
        }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # On error, exit silently (fail open)
        sys.stderr.write(f"Hook error: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
