---
name: list-schemes
description: List available schemes for an Xcode project or workspace using `xcodebuild -list`. Use to discover build schemes before building or testing.
---

# List Schemes

List available Xcode schemes for a project or workspace.

## Usage

```bash
# For a project
scripts/list-schemes.py --project /path/to/MyApp.xcodeproj

# For a workspace
scripts/list-schemes.py --workspace /path/to/MyApp.xcworkspace
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | One required | Path to .xcodeproj file |
| `--workspace` | One required | Path to .xcworkspace file |

Note: Use either `--project` or `--workspace`, not both.

## Examples

```bash
# List schemes for a project
scripts/list-schemes.py --project ./MyApp.xcodeproj

# List schemes for a workspace (common with CocoaPods)
scripts/list-schemes.py --workspace ./MyApp.xcworkspace
```

## Output

```json
{
  "success": true,
  "path": "/path/to/MyApp.xcodeproj",
  "type": "project",
  "schemes": [
    "MyApp",
    "MyAppTests",
    "MyAppUITests"
  ],
  "count": 3
}
```

## Notes

- Workspaces typically have more schemes (including pod schemes)
- Use the scheme name with `xcodebuild` `-scheme` argument
- This is often the first step before building or testing
