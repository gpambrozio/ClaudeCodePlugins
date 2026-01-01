---
name: macos-app
description: Launch and stop macOS applications. Use after building a macOS app to run it, or to terminate running macOS applications.
---

# macOS App Management

Launch and terminate macOS applications.

## Scripts

| Script | Purpose |
|--------|---------|
| `launch-mac-app.py` | Launch .app bundle |
| `stop-mac-app.py` | Quit running app |

## Usage

```bash
# Launch
scripts/launch-mac-app.py --app <path.app> [--args ...]

# Stop by bundle ID
scripts/stop-mac-app.py --bundle-id <id> [--force]

# Stop by app name
scripts/stop-mac-app.py --app-name "AppName" [--force]
```

Output JSON with `success` and operation details.

## App path

If the app was just built with `xcodebuild`, use the `--executable` flag with `xcsift` to display the executable path:

```bash
xcodebuild ... 2>&1 | tee /tmp/build.log | xcsift --format toon --warnings --executable
```

Or if you already have the build log:

```bash
cat /tmp/build.log | xcsift --format toon --warnings --executable
```

The executable path will be shown in the output after a successful build.
