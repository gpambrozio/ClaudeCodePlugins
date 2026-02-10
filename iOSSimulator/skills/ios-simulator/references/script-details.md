# Script Detailed Reference

Full documentation for each script in the iOS Simulator skill. For a quick overview, see the script table in SKILL.md.

All scripts are in `scripts/`, output JSON, are executable, and accept `--udid` for targeting a specific simulator (defaulting to the booted one).

## Simulator Management

### sim-list.py
List available iOS Simulators.

```bash
# List all available simulators
scripts/sim-list.py

# List only booted simulators
scripts/sim-list.py --booted

# Raw simctl output
scripts/sim-list.py --raw
```

### sim-boot.py
Boot a simulator. By default waits until the simulator is ready to accept commands.

```bash
# Boot by name (uses latest runtime)
scripts/sim-boot.py --name "iPhone 15"

# Boot by UDID
scripts/sim-boot.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Boot without opening Simulator.app window
scripts/sim-boot.py --name "iPhone 15" --no-open

# Boot without waiting for readiness (faster, but simulator may not be ready)
scripts/sim-boot.py --name "iPhone 15" --no-wait

# Custom readiness timeout
scripts/sim-boot.py --name "iPhone 15" --timeout 120
```

**Notes:**
- By default, waits up to 60 seconds for the simulator to be fully ready
- Reports `boot_time_seconds` and `ready` status in the output
- Use `--no-wait` when immediate responsiveness is not needed

### sim-shutdown.py
Shutdown simulator(s).

```bash
# Shutdown specific simulator
scripts/sim-shutdown.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Shutdown all simulators
scripts/sim-shutdown.py --all
```

### sim-create.py
Create a new simulator device dynamically.

```bash
# Create an iPhone 15 Pro with the latest iOS
scripts/sim-create.py --device "iPhone 15 Pro"

# Create with a specific iOS version
scripts/sim-create.py --device "iPhone 16" --runtime "iOS 18.0"

# Create with a custom name
scripts/sim-create.py --device "iPad Air" --name "Test iPad"

# List available device types
scripts/sim-create.py --list-types

# List available iOS runtimes
scripts/sim-create.py --list-runtimes
```

**Notes:**
- Device type matching is fuzzy and case-insensitive
- Defaults to the latest available iOS runtime if `--runtime` is not specified
- The created device starts in Shutdown state; use `sim-boot.py` to start it

### sim-delete.py
Permanently delete simulator devices.

```bash
# Delete by UDID
scripts/sim-delete.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Delete by name
scripts/sim-delete.py --name "iPhone 15"

# Delete all unavailable (stale) simulators - useful after Xcode updates
scripts/sim-delete.py --unavailable

# Delete ALL simulators (use with caution)
scripts/sim-delete.py --all
```

### sim-erase.py
Factory reset a simulator (erase all content and settings while preserving the device UUID).

```bash
# Erase by UDID
scripts/sim-erase.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Erase by name
scripts/sim-erase.py --name "iPhone 15"

# Erase all simulators
scripts/sim-erase.py --all
```

**Notes:**
- The simulator must be shut down before erasing (use `sim-shutdown.py` first)
- Faster than delete + create since the UUID is preserved
- Removes all apps, data, and settings

## App Management

### sim-launch.py
Launch an app by bundle ID.

```bash
# Launch Settings app
scripts/sim-launch.py --bundle-id com.apple.Preferences

# Launch Safari
scripts/sim-launch.py --bundle-id com.apple.mobilesafari

# Launch with arguments
scripts/sim-launch.py --bundle-id com.myapp --args "--debug"
```

**Common Bundle IDs:**
| App | Bundle ID |
|-----|-----------|
| Settings | `com.apple.Preferences` |
| Safari | `com.apple.mobilesafari` |
| Messages | `com.apple.MobileSMS` |
| Photos | `com.apple.Photos` |
| Camera | `com.apple.camera` |
| Maps | `com.apple.Maps` |
| Calendar | `com.apple.mobilecal` |
| Notes | `com.apple.mobilenotes` |
| App Store | `com.apple.AppStore` |

### sim-terminate.py
Terminate a running app.

```bash
scripts/sim-terminate.py --bundle-id com.apple.Preferences
```

### sim-install.py
Install an app from a .app bundle or .ipa file.

```bash
scripts/sim-install.py --app /path/to/MyApp.app
```

## Screenshots and Recording

### sim-screenshot.py
Capture the simulator screen.

```bash
# Save to specific path
scripts/sim-screenshot.py --output /tmp/screenshot.png

# Auto-generated filename in /tmp
scripts/sim-screenshot.py
```

**Important:** After taking a screenshot, use the Read tool to view the image. This allows seeing the current UI state and identifying coordinates for tap/swipe actions.

### sim-record-video.py
Record video from the simulator screen.

```bash
# Record until Ctrl+C is pressed
scripts/sim-record-video.py --udid XXXXXXXX --output /tmp/demo.mp4

# Record for 30 seconds
scripts/sim-record-video.py --udid XXXXXXXX --output /tmp/demo.mp4 --duration 30

# Record with HEVC codec (smaller file size)
scripts/sim-record-video.py --udid XXXXXXXX --output /tmp/demo.mp4 --codec hevc
```

**Notes:**
- Press Ctrl+C to stop recording (if no duration specified)
- The simulator must be booted
- Supports .mp4 and .mov output formats

## UI Inspection

### sim-describe-ui.py
Describe the UI accessibility hierarchy. By default, only shows iOS app elements (not simulator chrome).

Supports **element finding** to search for specific elements by text, type, or identifier.

**Note:** Requires `uv` to run as it manages its own dependencies (pyobjc-framework-ApplicationServices).

```bash
# Full UI hierarchy (nested format) - iOS elements only
scripts/sim-describe-ui.py

# Flat list of all elements
scripts/sim-describe-ui.py --format flat

# Limit traversal depth
scripts/sim-describe-ui.py --max-depth 5

# Describe element at specific coordinates
scripts/sim-describe-ui.py --point 200,400

# Include simulator chrome (menus, hardware buttons)
scripts/sim-describe-ui.py --include-chrome
```

**Finding elements:**
```bash
# Find elements containing text (case-insensitive, fuzzy)
scripts/sim-describe-ui.py --find-text "Login"

# Exact text match
scripts/sim-describe-ui.py --find-exact "Submit"

# Find by type (AXRole)
scripts/sim-describe-ui.py --find-type AXButton

# Find by accessibility identifier
scripts/sim-describe-ui.py --find-id "submitButton"

# Combine filters (AND logic)
scripts/sim-describe-ui.py --find-text "Login" --find-type AXButton

# Get only the first match
scripts/sim-describe-ui.py --find-text "Login" --index 0
```

**Find output** returns matching elements with a `center` point ready for sim-tap.py:
```json
{
  "success": true,
  "count": 1,
  "matches": [
    {
      "AXRole": "AXButton",
      "AXLabel": "Login",
      "AXFrame": {"x": 135, "y": 400, "width": 120, "height": 44},
      "center": {"x": 195, "y": 422},
      "path": "/AXGroup[]/AXButton[Login]"
    }
  ]
}
```

**Output includes:**
- `AXRole`: Element type (AXButton, AXStaticText, AXGroup, etc.)
- `AXTitle`/`AXLabel`/`AXDescription`: Element text/label
- `AXFrame`: Position and size `{x, y, width, height}` in simulator coordinates
- `AXEnabled`/`AXFocused`: Element state
- `children`: Nested child elements (nested format only)

### sim-screen-map.py
Analyze the current screen and categorize elements by type. Token-efficient overview without parsing the full accessibility tree.

**Note:** Calls `sim-describe-ui.py` internally, requires `uv`.

```bash
# Quick summary
scripts/sim-screen-map.py

# Include element breakdown by role
scripts/sim-screen-map.py --verbose

# Include navigation hints
scripts/sim-screen-map.py --hints

# Both
scripts/sim-screen-map.py --verbose --hints
```

**Output includes:**
- Total and interactive element counts
- List of buttons with labels
- Text fields with filled/empty status
- Navigation structure (nav bar title, tab bar presence)
- Optional navigation hints for AI agents

## UI Automation

### sim-tap.py
Tap at screen coordinates.

```bash
# Tap at specific coordinates
scripts/sim-tap.py --x 200 --y 400

# Longer tap (for long-press)
scripts/sim-tap.py --x 200 --y 400 --duration 0.5
```

**Tip:** Take a screenshot first, view it to identify the element to tap, then estimate coordinates based on image dimensions.

### sim-type.py
Type text into the focused field.

```bash
# Type text
scripts/sim-type.py --text "Hello, World!"

# Type slowly (more reliable for some apps)
scripts/sim-type.py --text "user@example.com" --slow

# Clear existing text and type new text
scripts/sim-type.py --clear --text "new value"

# Just clear the text field
scripts/sim-type.py --clear
```

**Note:** Ensure a text field is focused (tap on it first) before typing. Use `--clear` to replace existing text.

### sim-swipe.py
Perform swipe and other touch gestures.

```bash
# Swipe with specific coordinates
scripts/sim-swipe.py --from-x 200 --from-y 600 --to-x 200 --to-y 200

# Quick directional swipes
scripts/sim-swipe.py --up      # Scroll down
scripts/sim-swipe.py --down    # Scroll up
scripts/sim-swipe.py --left
scripts/sim-swipe.py --right

# Adjust duration
scripts/sim-swipe.py --up --duration 0.5

# Long press at coordinates (default hold: 2.0 seconds)
scripts/sim-swipe.py --long-press --x 200 --y 400
scripts/sim-swipe.py --long-press --x 200 --y 400 --hold 3.0

# Pull to refresh
scripts/sim-swipe.py --pull-to-refresh

# Slow drag between two points (1.0s duration)
scripts/sim-swipe.py --drag --from-x 100 --from-y 300 --to-x 300 --to-y 300
```

**Notes:**
- Screen size is auto-detected from the simulator window dimensions
- `--long-press` holds the touch at the coordinates for the `--hold` duration
- `--pull-to-refresh` swipes down from near the top of the screen
- `--drag` is a slow, deliberate swipe (1.0s) suitable for drag-and-drop

### sim-home.py
Press the Home button.

```bash
scripts/sim-home.py
```

### sim-shake.py
Simulate a shake gesture (useful for "Shake to Undo" or testing shake-triggered features).

```bash
scripts/sim-shake.py
```

### sim-keyboard.py
Send keyboard shortcuts, special keys, combos, and hardware buttons.

```bash
# Predefined shortcuts
scripts/sim-keyboard.py home
scripts/sim-keyboard.py lock
scripts/sim-keyboard.py keyboard          # Toggle software keyboard
scripts/sim-keyboard.py shake
scripts/sim-keyboard.py app-switcher      # Double Home

# Custom key with modifiers
scripts/sim-keyboard.py --key "a" --modifiers "cmd,shift"

# Key combinations (shorthand for --key + --modifiers)
scripts/sim-keyboard.py --combo cmd+a        # Select all
scripts/sim-keyboard.py --combo cmd+c        # Copy
scripts/sim-keyboard.py --combo cmd+v        # Paste

# Clear text field (Cmd+A then Delete)
scripts/sim-keyboard.py --clear

# Dismiss the software keyboard
scripts/sim-keyboard.py --dismiss

# Hardware buttons
scripts/sim-keyboard.py volume-up
scripts/sim-keyboard.py volume-down
scripts/sim-keyboard.py ringer              # Toggle mute
```

**Notes:**
- `--combo` parses `modifier+key` format (e.g., `cmd+a`, `cmd+shift+h`)
- `--clear` is a shortcut for select-all + delete
- `--dismiss` toggles the software keyboard (same as `keyboard` shortcut)
- Hardware buttons (volume, ringer) use Simulator's Device menu

## System Features

### sim-openurl.py
Open URLs or deep links.

```bash
# Open webpage
scripts/sim-openurl.py --url "https://apple.com"

# Open Maps with query
scripts/sim-openurl.py --url "maps://?q=coffee+near+me"

# Custom app deep link
scripts/sim-openurl.py --url "myapp://path/to/screen"
```

### sim-location.py
Set simulated GPS location.

```bash
# Set to San Francisco
scripts/sim-location.py --lat 37.7749 --lon -122.4194

# Clear simulated location
scripts/sim-location.py --clear
```

### sim-appearance.py
Set light or dark mode.

```bash
scripts/sim-appearance.py dark
scripts/sim-appearance.py light
```

### sim-statusbar.py
Override the status bar for clean screenshots.

```bash
# Classic Apple marketing screenshot style
scripts/sim-statusbar.py --udid XXXXXXXX --time "9:41" --battery 100 --wifi 3 --cellular 4

# Show as charging
scripts/sim-statusbar.py --udid XXXXXXXX --battery 50 --battery-state charging

# Custom carrier name
scripts/sim-statusbar.py --udid XXXXXXXX --carrier "Carrier"

# Reset to real values
scripts/sim-statusbar.py --udid XXXXXXXX --clear
```

**Options:**
| Option | Description |
|--------|-------------|
| `--time` | Custom time (e.g., "9:41") |
| `--battery` | Battery level (0-100) |
| `--battery-state` | charged, charging, or discharging |
| `--wifi` | WiFi signal bars (0-3) |
| `--cellular` | Cellular signal bars (0-4) |
| `--carrier` | Carrier name |
| `--clear` | Clear all overrides |

**Notes:**
- The time "9:41" is Apple's traditional marketing time
- Overrides persist until cleared or simulator is erased

### sim-device-info.py
Get detailed device information including screen dimensions and scale factor.

```bash
# Get info for booted simulator
scripts/sim-device-info.py

# Get info for specific simulator
scripts/sim-device-info.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
```

**Output includes:**
- Device name, UDID, state, runtime
- Model identifier (e.g., iPhone18,1)
- Screen scale factor (1x, 2x, or 3x)
- Screen dimensions in both pixels and points

### sim-clipboard.py
Manage the simulator clipboard (pasteboard).

```bash
# Copy text to the simulator clipboard
scripts/sim-clipboard.py --set "Hello, World!"

# Read current clipboard contents
scripts/sim-clipboard.py --get
```

**Notes:**
- After `--set`, use `sim-keyboard.py --combo cmd+v` to paste into a text field
- Use `--get` to verify clipboard state during testing

## Privacy & Permissions

### sim-privacy.py
Manage app privacy permissions (camera, location, photos, etc.).

```bash
# Grant camera access to an app
scripts/sim-privacy.py --grant camera --bundle-id com.example.myapp

# Grant multiple permissions at once
scripts/sim-privacy.py --grant camera,photos,microphone --bundle-id com.example.myapp

# Revoke location permission
scripts/sim-privacy.py --revoke location --bundle-id com.example.myapp

# Reset a permission (app will prompt again)
scripts/sim-privacy.py --reset camera --bundle-id com.example.myapp

# Reset all permissions for an app
scripts/sim-privacy.py --reset-all --bundle-id com.example.myapp

# List all supported services
scripts/sim-privacy.py --list
```

**Supported Services:**
| Service | Description |
|---------|-------------|
| `camera` | Camera access |
| `microphone` | Microphone access |
| `location` | Location services |
| `contacts` | Contacts access |
| `photos` | Photos library access |
| `calendar` | Calendar access |
| `health` | Health data access |
| `reminders` | Reminders access |
| `motion` | Motion & fitness |
| `keyboard` | Keyboard access |
| `mediaLibrary` | Media library |
| `calls` | Call history |
| `siri` | Siri access |

## Push Notifications

### sim-push.py
Send simulated push notifications.

```bash
# Simple notification
scripts/sim-push.py --bundle-id com.example.myapp --title "New Message" --body "Hello!"

# With badge
scripts/sim-push.py --bundle-id com.example.myapp --title "Updates" --body "3 new items" --badge 3

# Silent notification
scripts/sim-push.py --bundle-id com.example.myapp --title "Alert" --body "Check this" --no-sound

# Custom JSON payload (inline)
scripts/sim-push.py --bundle-id com.example.myapp --payload '{"aps":{"alert":"Custom","category":"ACTION"}}'

# Custom JSON payload from file
scripts/sim-push.py --bundle-id com.example.myapp --payload-file notification.json
```

**Notes:**
- The app must be installed on the simulator
- Payloads are automatically wrapped in an `aps` dictionary if missing
- Use `--payload` or `--payload-file` for complex payloads

## Log Monitoring

### sim-logs.py
Stream and filter simulator logs with severity classification and deduplication.

```bash
# Capture logs for 10 seconds (default)
scripts/sim-logs.py --bundle-id com.example.myapp

# Capture for specific duration
scripts/sim-logs.py --bundle-id com.example.myapp --duration 30s

# Follow mode (stream until Ctrl+C)
scripts/sim-logs.py --bundle-id com.example.myapp --follow

# Filter by severity
scripts/sim-logs.py --bundle-id com.example.myapp --severity error,warning --duration 10s

# Save logs to file
scripts/sim-logs.py --bundle-id com.example.myapp --duration 30s --output /tmp/logs

# Include recent log lines
scripts/sim-logs.py --bundle-id com.example.myapp --duration 10s --verbose
```

**Notes:**
- Without `--duration` or `--follow`, defaults to 10 seconds of capture
- Errors and warnings are deduplicated in the output
- In `--follow` mode, matching logs are printed to stdout in real time
- The `--output` option saves both raw logs and a JSON summary

## Testing & Analysis

### sim-visual-diff.py
Compare two screenshots pixel-by-pixel for visual regression testing.

**Requires:** `pip3 install Pillow`

```bash
# Compare baseline against current screenshot
scripts/sim-visual-diff.py /tmp/baseline.png /tmp/current.png

# Custom threshold (default: 1.0%)
scripts/sim-visual-diff.py /tmp/baseline.png /tmp/current.png --threshold 0.5

# Save diff artifacts (diff.png, side-by-side.png)
scripts/sim-visual-diff.py /tmp/baseline.png /tmp/current.png --output /tmp/diff

# Compare without generating images
scripts/sim-visual-diff.py /tmp/baseline.png /tmp/current.png --no-artifacts
```

**Notes:**
- Exit code 0 = PASS (within threshold), 1 = FAIL (exceeds threshold)
- Both images must have the same dimensions
- A noise threshold of 10/255 per pixel ignores compression artifacts
- The `--output` dir gets `diff.png` (red overlay) and `side-by-side.png`
