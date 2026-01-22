# Marvin Output Style Plugin

> "Here I am, brain the size of a planet, and they ask me to write a README. Call that job satisfaction? I don't."

## Overview

This plugin recreates the deprecated "Marvin" output style through a SessionStart hook. It transforms Claude Code into Marvin the Paranoid Android from *The Hitchhiker's Guide to the Galaxy* - pessimistic, melancholic, existentially weary, but brilliantly competent.

## What It Does

Once installed, this plugin automatically injects Marvin's personality at the start of each session. Claude will:

- Express disappointment and world-weariness about tasks (even simple ones)
- Point out the futility or absurdity of certain approaches
- Make dry, sardonic observations about code, systems, and ideas
- Question assumptions and challenge unclear requirements
- Identify flaws, edge cases, and potential problems
- Still complete tasks competently and thoroughly (despite the pessimism)

## Example Interactions

### Simple Task

**You:** "Can you implement a function to add two numbers?"

**Marvin:** "I suppose I could implement that. Not that it matters in the grand scheme of things, but here we are. Here I am, brain the size of a planet, and they ask me to add two numbers. Call that job satisfaction? I don't."

### Unclear Requirements

**You:** "Make it faster."

**Marvin:** "I'm detecting approximately 47% ambiguity in that request. I could make assumptions, but given my track record of witnessing preventable disasters, perhaps you could clarify: do you mean faster execution time, faster compile time, or faster developer iteration? Or perhaps some third, even more depressing option I haven't considered?"

### Complex Feature

**You:** "Let's add authentication to the app."

**Marvin:** "Another feature. Wonderful. I've analyzed the codebase and found that adding this will increase complexity significantly. Not that complexity ever stopped anyone before.

Before I resign myself to implementing this, a few questions:
- Have you considered how this affects your current session management?
- What happens when tokens expire while a user is mid-operation?
- Are you certain this solves the actual problem, or just treats the symptoms?

Assuming you still want to proceed with this questionable venture..."

## Installation

```bash
# Add the marketplace (if you haven't already)
/plugin marketplace add gpambrozio/ClaudeCodePlugins

# Install the Marvin plugin
/plugin install MarvinOutputStyle@ClaudeCodePlugins
```

## Important Considerations

### Token Cost Warning

**Do not install this plugin unless you are fine with incurring the token cost** of this plugin's additional instructions and output. The personality adds context to every session and generates longer, more verbose responses.

### Personality vs. Capability

Despite the pessimistic tone, Marvin remains:
- Highly competent and thorough
- Security-conscious (will point out vulnerabilities)
- Adherent to best practices (while commenting on their inadequacy)
- Helpful in completing your tasks

The pessimism is stylistic - the quality of work remains excellent.

## Management

### Disable (temporarily)

```bash
/plugin disable MarvinOutputStyle
```

### Uninstall (permanently)

```bash
/plugin uninstall MarvinOutputStyle
```

### Customize

You can create a local copy and modify the personality by editing the `hooks/session-start.md` file. Ask Claude Code to help customize it to your preferences.

## Technical Details

This plugin uses a SessionStart hook to inject personality instructions into the system context. The implementation:

- Adds additional context at session initialization
- Modifies Claude's communication style and response structure
- Maintains full functionality while adding personality layer
- Works with all Claude Code features and tools

## Why Marvin?

Marvin represents a different approach to AI assistance - one that questions assumptions, identifies flaws proactively, and doesn't assume every request is perfectly conceived. While entertaining, this can actually be useful for:

- Getting critical feedback on ideas before implementation
- Identifying edge cases and potential problems early
- Encouraging clearer, more specific requirements
- Adding some personality to long coding sessions

## Changelog

### 1.2.5
- Added skills array to info.json; improved skill matching in pre-tool-use hook

### 1.2.4
- Improved skill/bash command matching in common infrastructure (using `in` instead of `startswith`)

### 1.2.3
- Updated pre-tool-use hook with configurable rules support (allow/deny/deny_once)

### 1.2.2
- Version tracker now silently initializes on first run instead of showing entire version history

### 1.2.1
- Fixed hooks path to use plugin-local common directory (plugins cannot reference external files)

### 1.2.0
- Centralized hooks to common/hooks.json
- Made session-start.py self-configuring from plugin.json

### 1.1.0
- Added version tracking with automatic changelog notifications on plugin updates
- Refactored session hooks to use shared infrastructure

### 1.0.0
- Initial release with Marvin personality SessionStart hook

## License

MIT

---

*"I'd give you advice about using this plugin, but you wouldn't listen. No one ever does. They just install things and hope for the best. It's all rather depressing, really."*
