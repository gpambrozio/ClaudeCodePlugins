---
name: launch-mac-app
description: Launch a macOS application from its .app bundle. Use after building a macOS app to run it for testing.
---

# Launch macOS App

Launch a macOS application.

## Usage

```bash
scripts/launch-mac-app.py --app /path/to/MyApp.app [--args ...]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--app` | Yes | Path to the .app bundle |
| `--args` | No | Arguments to pass to the app |

## Examples

```bash
# Launch an app
scripts/launch-mac-app.py --app ~/DerivedData/MyApp/Build/Products/Debug/MyApp.app

# Launch with arguments
scripts/launch-mac-app.py --app ./MyApp.app --args --debug --config test
```

## Output

```json
{
  "success": true,
  "message": "App launched successfully",
  "app_path": "/path/to/MyApp.app"
}
```

## Notes

- Uses the macOS `open` command
- The app will open in a new window
- Use stop-mac-app.py to terminate the app
