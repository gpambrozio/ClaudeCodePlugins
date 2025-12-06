---
name: stop-mac-app
description: Stop a running macOS application by bundle ID or app name. Use to terminate apps for testing or cleanup.
---

# Stop macOS App

Terminate a running macOS application.

## Usage

```bash
# By bundle identifier
scripts/stop-mac-app.py --bundle-id com.example.MyApp

# By app name
scripts/stop-mac-app.py --app-name "MyApp"

# Force quit
scripts/stop-mac-app.py --bundle-id com.example.MyApp --force
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--bundle-id` | One required | Bundle identifier of the app |
| `--app-name` | One required | Name of the app (as in Activity Monitor) |
| `--force` | No | Force quit the app (SIGKILL) |

## Examples

```bash
# Graceful quit by bundle ID
scripts/stop-mac-app.py --bundle-id com.example.MyApp

# Force quit by name
scripts/stop-mac-app.py --app-name "MyApp" --force
```

## Output

```json
{
  "success": true,
  "message": "App quit successfully",
  "identifier": "com.example.MyApp"
}
```

## Notes

- Graceful quit uses AppleScript `tell app to quit`
- Force quit uses SIGKILL (app won't save state)
- Returns success even if app wasn't running
