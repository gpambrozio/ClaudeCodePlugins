---
allowed-tools: mcp__plugin_SwiftScaffolding_XcodeBuildMCP, AskUserQuestion
description: Create an iOS or MacOS project scaffolginf using `XCodeBuildMCP` mcp
---
Use the `AskUserQuestion` tool to ask the user:
* If this is a MacOS project or an iOS project.
* The name of the project.
* The project bundle identifier.

If it is an iOS project, use the `scaffold_ios_project` tool in `XCodeBuildMCP` mcp with these parameters:

projectName: <PROJECT_NAME>
outputPath: current folder
bundleIdentifier: <BUNDLE_IDENTIFIER>
displayName: <PROJECT_NAME>
target device family: universal
deploymentTarget: 18.0
supported orientations: all for both iphone and ipad

If it is a MacOS project, use the `scaffold_macos_project` tool in `XCodeBuildMCP` mcp with these parameters:

projectName: <PROJECT_NAME>
outputPath: current folder
bundleIdentifier: <BUNDLE_IDENTIFIER>
displayName: <PROJECT_NAME>
deploymentTarget: 15.0
