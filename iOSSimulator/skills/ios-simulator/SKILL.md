---
name: ios-simulator
description: Control iOS Simulators - boot/shutdown, launch apps, take screenshots, tap/swipe/type for UI automation, set location, and more. Use this skill whenever you need to interact with an iOS Simulator.
---

# iOS Simulator Control

Control iOS Simulators using native macOS tools. No additional dependencies required beyond Xcode Command Line Tools.

## Prerequisites

- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3 (pre-installed on macOS)

## Running the scripts.

- All scripts are executable and have the proper shebang line so no need to prefix it with `python3`.
- All scripts are in the `scripts/` directory.
- All scripts output JSON.
- All scripts have proper docstrings explaining the arguments.
- For more complicated workflows you can also write your own scripts using the functions provided by the scripts or just using them as code sample to write your own scripts.

## Quick Start Workflow

```bash
# 1. List available simulators
scripts/sim-list.py

# 2. Boot a simulator
scripts/sim-boot.py --name "iPhone 15"

# 3. Take a screenshot (Claude can view this!)
scripts/sim-screenshot.py --output /tmp/screen.png

# 4. Read the screenshot to see the UI
# Use the Read tool on /tmp/screen.png

# 5. Tap at coordinates you identify from the screenshot
scripts/sim-tap.py --x 200 --y 400

# 6. Type text
scripts/sim-type.py --text "Hello, World!"
```

## Choosing a simulator

If the user asks for a specific simulator, use the `scripts/sim-list.py` to find the most appropriate simulator. If the simulator is not booted, use the `scripts/sim-boot.py` to boot it. Then use the simulator udid for the following commands.

If the user doesn't specify a simulator, use the `scripts/sim-list.py` and choose:
- If one or more simulators are booted, use the most recent model with the latest OS.
- If no simulator is booted, use the `scripts/sim-boot.py` to boot the most recent model with the latest OS.

## Script Reference

All scripts are in `scripts/` and output JSON.

### Simulator Management

#### sim-list.py
List available iOS Simulators.

```bash
# List all available simulators
scripts/sim-list.py

# List only booted simulators
scripts/sim-list.py --booted

# Raw simctl output
scripts/sim-list.py --raw
```

#### sim-boot.py
Boot a simulator.

```bash
# Boot by name (uses latest runtime)
scripts/sim-boot.py --name "iPhone 15"

# Boot by UDID
scripts/sim-boot.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Boot without opening Simulator.app window
scripts/sim-boot.py --name "iPhone 15" --no-open
```

#### sim-shutdown.py
Shutdown simulator(s).

```bash
# Shutdown specific simulator
scripts/sim-shutdown.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Shutdown all simulators
scripts/sim-shutdown.py --all
```

### App Management

#### sim-launch.py
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

#### sim-terminate.py
Terminate a running app.

```bash
scripts/sim-terminate.py --bundle-id com.apple.Preferences
```

#### sim-install.py
Install an app from a .app bundle or .ipa file.

```bash
scripts/sim-install.py --app /path/to/MyApp.app
```

### Screenshots

#### sim-screenshot.py
Capture the simulator screen.

```bash
# Save to specific path
scripts/sim-screenshot.py --output /tmp/screenshot.png

# Auto-generated filename in /tmp
scripts/sim-screenshot.py
```

**Important:** After taking a screenshot, use the Read tool to view the image. This allows you to see the current UI state and identify coordinates for tap/swipe actions.

### UI Inspection

#### sim-describe-ui.py
Describe the UI accessibility hierarchy of the iOS app running in the simulator. By default, only shows iOS app elements (not simulator chrome like menus or hardware buttons).

**Note:** This script requires `uv` to run as it manages its own dependencies (pyobjc-framework-ApplicationServices).

```bash
# Get full UI hierarchy (nested format) - iOS elements only
scripts/sim-describe-ui.py

# Get flat list of all elements
scripts/sim-describe-ui.py --format flat

# Limit traversal depth
scripts/sim-describe-ui.py --max-depth 5

# Describe element at specific coordinates
scripts/sim-describe-ui.py --point 200,400

# Include simulator chrome (menus, hardware buttons) with absolute screen coordinates
scripts/sim-describe-ui.py --include-chrome
```

**Output includes:**
- `AXRole`: Element type (AXButton, AXStaticText, AXGroup, etc.)
- `AXTitle`/`AXLabel`/`AXDescription`: Element text/label
- `AXFrame`: Position and size `{x, y, width, height}` in **simulator coordinates**
- `AXEnabled`/`AXFocused`: Element state
- `children`: Nested child elements (in nested format)

**Coordinates are ready to use with sim-tap.py:**
```bash
# Find a button by label
scripts/sim-describe-ui.py --format flat | jq '.elements[] | select(.AXDescription == "Login")'
# Output: {"AXRole": "AXButton", "AXLabel": "Login", "AXFrame": {"x": 180, "y": 500, "width": 120, "height": 44}, ...}

# Tap it directly using the coordinates from AXFrame
scripts/sim-tap.py --x 180 --y 500
```

**Use cases:**
- Discover button labels and identifiers for automation
- Find exact element positions without guessing from screenshots
- Debug why taps aren't hitting the expected elements
- Understand the app's view hierarchy

### UI Automation

#### sim-tap.py
Tap at screen coordinates.

```bash
# Tap at specific coordinates
scripts/sim-tap.py --x 200 --y 400

# Longer tap (for long-press)
scripts/sim-tap.py --x 200 --y 400 --duration 0.5
```

**Tip:** Take a screenshot first, view it to identify the element you want to tap, then estimate coordinates based on the image dimensions.

#### sim-type.py
Type text into the focused field.

```bash
# Type text
scripts/sim-type.py --text "Hello, World!"

# Type slowly (more reliable for some apps)
scripts/sim-type.py --text "user@example.com" --slow
```

**Note:** Make sure a text field is focused (tap on it first) before typing.

#### sim-swipe.py
Perform swipe gestures.

```bash
# Swipe with specific coordinates
scripts/sim-swipe.py --from-x 200 --from-y 600 --to-x 200 --to-y 200

# Quick directional swipes
scripts/sim-swipe.py --up      # Scroll down
scripts/sim-swipe.py --down    # Scroll up
scripts/sim-swipe.py --left    # Swipe left
scripts/sim-swipe.py --right   # Swipe right

# Adjust duration
scripts/sim-swipe.py --up --duration 0.5
```

#### sim-home.py
Press the Home button.

```bash
scripts/sim-home.py
```

#### sim-shake.py
Simulate a shake gesture (useful for "Shake to Undo" or testing shake-triggered features).

```bash
scripts/sim-shake.py
```

#### sim-keyboard.py
Send keyboard shortcuts and special keys.

```bash
# Press Home button
scripts/sim-keyboard.py home

# Lock screen
scripts/sim-keyboard.py lock

# Toggle software keyboard
scripts/sim-keyboard.py keyboard

# Shake gesture
scripts/sim-keyboard.py shake

# App switcher (double Home)
scripts/sim-keyboard.py app-switcher

# Custom key with modifiers
scripts/sim-keyboard.py --key "a" --modifiers "cmd,shift"
```

### System Features

#### sim-openurl.py
Open URLs or deep links.

```bash
# Open webpage
scripts/sim-openurl.py --url "https://apple.com"

# Open Maps with query
scripts/sim-openurl.py --url "maps://?q=coffee+near+me"

# Custom app deep link
scripts/sim-openurl.py --url "myapp://path/to/screen"
```

#### sim-location.py
Set simulated GPS location.

```bash
# Set to San Francisco
scripts/sim-location.py --lat 37.7749 --lon -122.4194

# Set to New York
scripts/sim-location.py --lat 40.7128 --lon -74.0060

# Clear simulated location
scripts/sim-location.py --clear
```

#### sim-appearance.py
Set light or dark mode.

```bash
scripts/sim-appearance.py dark
scripts/sim-appearance.py light
```

#### sim-device-info.py
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

## Automation Workflow Example

Here's a typical workflow to automate UI testing:

```bash
# 1. Ensure simulator is running
scripts/sim-list.py --booted

# If none booted:
scripts/sim-list.py

# Then choose the most appropriate simulator to boot
scripts/sim-boot.py --name "iPhone 15"

# 2. Launch the app
scripts/sim-launch.py --bundle-id com.example.myapp

# 3. Wait for app to load, then screenshot
sleep 2
scripts/sim-screenshot.py --output /tmp/step1.png
# View /tmp/step1.png with Read tool

# 4. Based on screenshot, tap the login button (e.g., at 200,500)
scripts/sim-tap.py --x 200 --y 500

# 5. Screenshot to see login form
scripts/sim-screenshot.py --output /tmp/step2.png
# View /tmp/step2.png

# 6. Tap email field and type
scripts/sim-tap.py --x 200 --y 300
scripts/sim-type.py --text "user@example.com"

# 7. Tap password field and type
scripts/sim-tap.py --x 200 --y 400
scripts/sim-type.py --text "password123"

# 8. Tap login button
scripts/sim-tap.py --x 200 --y 550

# 9. Verify result
sleep 2
scripts/sim-screenshot.py --output /tmp/step3.png
# View /tmp/step3.png to confirm login success
```

## Coordinate System

### Points vs Pixels

iOS uses a **point-based** coordinate system that is independent of screen resolution:

| Concept | Description |
|---------|-------------|
| **Points** | Logical coordinates used by `sim-tap.py`, `sim-swipe.py`, and `sim-describe-ui.py` |
| **Pixels** | Physical screen pixels in screenshots |
| **Scale Factor** | Multiplier to convert points to pixels (1x, 2x, or 3x for Retina displays) |

**Relationship:** `pixels = points × scale_factor`

### Screenshot to Tap Coordinate Conversion

Screenshots are captured at **native pixel resolution**, but tap commands use **points**. The `sim-screenshot.py` output includes screen info to help with conversion:

```json
{
  "success": true,
  "path": "/tmp/screenshot.png",
  "screen": {
    "scale": 3,
    "width_pixels": 1206,
    "height_pixels": 2622,
    "width_points": 402,
    "height_points": 874
  }
}
```

**To convert pixel coordinates from a screenshot to tap coordinates:**

```python
# If you identify an element at pixel (600, 900) in the screenshot:
scale = 3  # From screenshot output
tap_x = 600 / scale  # = 200 points
tap_y = 900 / scale  # = 300 points
```

### Coordinate Origin

- Origin (0, 0) is the **top-left** corner of the simulator screen
- X increases to the right
- Y increases downward

## Troubleshooting

### "No booted simulator found"
Boot a simulator first:
```bash
scripts/sim-list.py

# Then choose the most appropriate simulator to boot
scripts/sim-boot.py --name "iPhone 15"
```

### Taps not registering at correct position
- The coordinate translation includes estimated bezel offsets
- Take a screenshot and verify the visible area matches your expectations
- Try adjusting coordinates slightly

### Text not typing
- Ensure a text field is focused by tapping on it first
- Try using `--slow` flag for more reliable character-by-character input

### Quartz module not found
- The tap/swipe scripts require the `pyobjc-framework-Quartz` module
- This is usually pre-installed on macOS with Xcode
- Fallback to AppleScript will be used if Quartz is unavailable

### Screenshots show wrong simulator
- If multiple simulators are booted, specify `--udid` explicitly
- Use `scripts/sim-list.py --booted` to see all running simulators

## JSON Output Schemas

All scripts output JSON to stdout. Every response includes a `success` boolean field.

### Standard Success Response
```json
{
  "success": true,
  "message": "Description of what was done",
  "udid": "SIMULATOR-UDID"
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": "Description of what went wrong. Helpful hint if available.",
  "error_category": "category_name"
}
```

**Error Categories:**
| Category | Description |
|----------|-------------|
| `already_booted` | Simulator is already running (treated as success) |
| `already_shutdown` | Simulator is already shut down (treated as success) |
| `app_not_running` | App is not running when terminating (treated as success) |
| `invalid_device` | Unknown or invalid simulator UDID |
| `invalid_bundle` | App not installed or invalid bundle ID |
| `app_not_found` | Cannot find or launch the app |
| `install_failed` | App installation failed |
| `launch_failed` | App failed to launch |
| `url_denied` | URL scheme not registered |
| `location_failed` | Failed to set location |
| `screenshot_failed` | Failed to capture screenshot |
| `timeout` | Operation timed out |
| `unknown` | Unrecognized error |

**Note:** Some "errors" are actually success conditions (marked above). For example, trying to boot an already-booted simulator returns:
```json
{
  "success": true,
  "message": "The simulator is already running.",
  "note": "Unable to boot device in current state: Booted",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

### Script-Specific Schemas

#### sim-list.py
```json
{
  "success": true,
  "count": 5,
  "simulators": [
    {
      "name": "iPhone 15",
      "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
      "state": "Booted",
      "runtime": "iOS 17.0"
    }
  ]
}
```

#### sim-boot.py
```json
{
  "success": true,
  "message": "Simulator booted successfully",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "name": "iPhone 15",
  "runtime": "iOS-17-0"
}
```

#### sim-screenshot.py
```json
{
  "success": true,
  "message": "Screenshot saved",
  "path": "/tmp/sim-screenshot-1234567890.png",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "size_bytes": 123456,
  "screen": {
    "scale": 3,
    "width_pixels": 1206,
    "height_pixels": 2622,
    "width_points": 402,
    "height_points": 874
  }
}
```
**Note:** The `screen` object provides the scale factor needed to convert pixel coordinates from the screenshot to point coordinates for `sim-tap.py`. Divide pixel coordinates by `scale` to get tap coordinates.

#### sim-tap.py
```json
{
  "success": true,
  "message": "Tapped at (200, 400)",
  "screen_x": 200,
  "screen_y": 400,
  "window_x": 320,
  "window_y": 478,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

#### sim-swipe.py
```json
{
  "success": true,
  "message": "Swiped from (195, 500) to (195, 200)",
  "from": {"x": 195, "y": 500},
  "to": {"x": 195, "y": 200},
  "duration": 0.3,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

#### sim-type.py
```json
{
  "success": true,
  "message": "Typed 12 characters",
  "text_length": 12,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

#### sim-launch.py
```json
{
  "success": true,
  "message": "Launched com.apple.Preferences",
  "bundle_id": "com.apple.Preferences",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "pid": 12345
}
```

#### sim-location.py
```json
{
  "success": true,
  "message": "Location set",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

#### sim-device-info.py
```json
{
  "success": true,
  "name": "iPhone 17 Pro",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "state": "Booted",
  "runtime": "iOS-26-1",
  "device_type": "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro",
  "model_identifier": "iPhone18,1",
  "screen": {
    "scale": 3,
    "width_pixels": 1206,
    "height_pixels": 2622,
    "width_points": 402,
    "height_points": 874,
    "ppi": 460
  }
}
```

#### sim-describe-ui.py (nested format)
```json
{
  "success": true,
  "simulator": {
    "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
    "name": "iPhone 15"
  },
  "element_count": 42,
  "root": {
    "AXRole": "AXGroup",
    "AXFrame": {"x": 0, "y": 0, "width": 390, "height": 844},
    "children": [
      {
        "AXRole": "AXButton",
        "AXLabel": "Login",
        "AXFrame": {"x": 135, "y": 400, "width": 120, "height": 44}
      }
    ]
  }
}
```

#### sim-describe-ui.py (flat format)
```json
{
  "success": true,
  "simulator": {
    "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
    "name": "iPhone 15"
  },
  "element_count": 42,
  "elements": [
    {
      "AXRole": "AXButton",
      "AXLabel": "Login",
      "AXFrame": {"x": 135, "y": 400, "width": 120, "height": 44},
      "AXEnabled": true
    }
  ]
}
