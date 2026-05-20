---
allowed-tools: AskUserQuestion, mcp__plugin_SwiftScaffolding_XcodeBuildMCP
description: Create an iOS or macOS project using XcodeBuildMCP
---
Ask the user for the project platform, project name, and bundle identifier.
Use the host's native structured question mechanism if available; otherwise ask
normally in chat.

If it is an iOS project, use the `scaffold_ios_project` tool in XcodeBuildMCP with these parameters:

projectName: <PROJECT_NAME>
outputPath: current folder
bundleIdentifier: <BUNDLE_IDENTIFIER>
displayName: <PROJECT_NAME>
target device family: universal
deploymentTarget: 18.0
supported orientations: all for both iPhone and iPad

If it is a macOS project, use the `scaffold_macos_project` tool in XcodeBuildMCP with these parameters:

projectName: <PROJECT_NAME>
outputPath: current folder
bundleIdentifier: <BUNDLE_IDENTIFIER>
displayName: <PROJECT_NAME>
deploymentTarget: 15.0
