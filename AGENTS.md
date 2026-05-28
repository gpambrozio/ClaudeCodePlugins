# Agent Guidance

This repository uses the Claude Code plugin marketplace format, including
`.claude-plugin` manifests and `CLAUDE_PLUGIN_*` environment variables. Treat
those names as compatibility contracts, not as a reason to make agent-facing
instructions Claude-specific.

Use `CLAUDE.md` for the full repository architecture and release workflow. When
editing skills, READMEs, or session-start context, prefer neutral
terms like "agent", "assistant", "host", or "session" unless the text is about a
Claude Code-specific file, command, environment variable, or historical
changelog entry.

Keep skill bodies portable by asking for the host's native mechanism instead of
naming a specific tool unless a plugin contract requires the concrete name.

Keep new runtime checks and packaging expectations covered by:

```bash
python3 -m unittest discover -s tests -v
```
