---
name: scaffolding
description: Use when creating or scaffolding a new iOS or macOS Swift project with XcodeBuildMCP.
---

# Scaffolding

Use this skill to create a new Swift project from the current folder.

## Inputs

Ask the user for:

- Platform: iOS or macOS
- Project name
- Bundle identifier

Use the host's native structured question mechanism if available; otherwise ask normally in chat.

## iOS Project

Use the `scaffold_ios_project` tool in XcodeBuildMCP with:

- `projectName`: project name
- `outputPath`: current folder
- `bundleIdentifier`: bundle identifier
- `displayName`: project name
- Target device family: universal
- Deployment target: 18.0
- Supported orientations: all for both iPhone and iPad

## macOS Project

Use the `scaffold_macos_project` tool in XcodeBuildMCP with:

- `projectName`: project name
- `outputPath`: current folder
- `bundleIdentifier`: bundle identifier
- `displayName`: project name
- Deployment target: 15.0
