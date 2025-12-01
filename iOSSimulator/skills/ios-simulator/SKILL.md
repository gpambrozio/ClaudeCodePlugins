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

## Quick Start Workflow

```bash
# 1. List available simulators
python3 scripts/sim-list.py

# 2. Boot a simulator
python3 scripts/sim-boot.py --name "iPhone 15"

# 3. Take a screenshot (Claude can view this!)
python3 scripts/sim-screenshot.py --output /tmp/screen.png

# 4. Read the screenshot to see the UI
# Use the Read tool on /tmp/screen.png

# 5. Tap at coordinates you identify from the screenshot
python3 scripts/sim-tap.py --x 200 --y 400

# 6. Type text
python3 scripts/sim-type.py --text "Hello, World!"
```

## Script Reference

All scripts are in `${CLAUDE_PLUGIN_ROOT}/skills/ios-simulator/scripts/` and output JSON.

### Simulator Management

#### sim-list.py
List available iOS Simulators.

```bash
# List all available simulators
python3 sim-list.py

# List only booted simulators
python3 sim-list.py --booted

# Raw simctl output
python3 sim-list.py --raw
```

#### sim-boot.py
Boot a simulator.

```bash
# Boot by name (uses latest runtime)
python3 sim-boot.py --name "iPhone 15"

# Boot by UDID
python3 sim-boot.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Boot without opening Simulator.app window
python3 sim-boot.py --name "iPhone 15" --no-open
```

#### sim-shutdown.py
Shutdown simulator(s).

```bash
# Shutdown specific simulator
python3 sim-shutdown.py --udid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Shutdown all simulators
python3 sim-shutdown.py --all
```

### App Management

#### sim-launch.py
Launch an app by bundle ID.

```bash
# Launch Settings app
python3 sim-launch.py --bundle-id com.apple.Preferences

# Launch Safari
python3 sim-launch.py --bundle-id com.apple.mobilesafari

# Launch with arguments
python3 sim-launch.py --bundle-id com.myapp --args "--debug"
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
python3 sim-terminate.py --bundle-id com.apple.Preferences
```

#### sim-install.py
Install an app from a .app bundle or .ipa file.

```bash
python3 sim-install.py --app /path/to/MyApp.app
```

### UI Inspection

#### sim-describe-ui.py
Get accessibility information about UI elements on screen. Uses macOS Accessibility APIs to inspect the Simulator window.

```bash
# Get full UI element tree
python3 sim-describe-ui.py

# Get only tappable elements (buttons, links, etc.)
python3 sim-describe-ui.py --buttons

# Get only text input fields
python3 sim-describe-ui.py --text-fields

# Get flat list of tappable elements with coordinates
python3 sim-describe-ui.py --flat
```

**Output includes:**
- `role`: Element type (Button, TextField, StaticText, etc.)
- `label`: Accessibility label/title
- `value`: Current value (for text fields)
- `position`: Screen coordinates `{x, y}`
- `size`: Element dimensions `{width, height}`
- `center`: Center point for tapping `{x, y}`

**Note:** First run may prompt for Accessibility permissions. Grant access in System Preferences > Security & Privacy > Privacy > Accessibility.

**Tip:** Use `--flat` to get a simple list of all interactive elements with their center coordinates for easy tapping.

### Screenshots

#### sim-screenshot.py
Capture the simulator screen.

```bash
# Save to specific path
python3 sim-screenshot.py --output /tmp/screenshot.png

# Auto-generated filename in /tmp
python3 sim-screenshot.py
```

**Important:** After taking a screenshot, use the Read tool to view the image. This allows you to see the current UI state and identify coordinates for tap/swipe actions.

### UI Automation

#### sim-tap.py
Tap at screen coordinates.

```bash
# Tap at specific coordinates
python3 sim-tap.py --x 200 --y 400

# Longer tap (for long-press)
python3 sim-tap.py --x 200 --y 400 --duration 0.5
```

**Tip:** Take a screenshot first, view it to identify the element you want to tap, then estimate coordinates based on the image dimensions.

#### sim-type.py
Type text into the focused field.

```bash
# Type text
python3 sim-type.py --text "Hello, World!"

# Type slowly (more reliable for some apps)
python3 sim-type.py --text "user@example.com" --slow
```

**Note:** Make sure a text field is focused (tap on it first) before typing.

#### sim-swipe.py
Perform swipe gestures.

```bash
# Swipe with specific coordinates
python3 sim-swipe.py --from-x 200 --from-y 600 --to-x 200 --to-y 200

# Quick directional swipes
python3 sim-swipe.py --up      # Scroll down
python3 sim-swipe.py --down    # Scroll up
python3 sim-swipe.py --left    # Swipe left
python3 sim-swipe.py --right   # Swipe right

# Adjust duration
python3 sim-swipe.py --up --duration 0.5
```

#### sim-home.py
Press the Home button.

```bash
python3 sim-home.py
```

#### sim-shake.py
Simulate a shake gesture (useful for "Shake to Undo" or testing shake-triggered features).

```bash
python3 sim-shake.py
```

#### sim-keyboard.py
Send keyboard shortcuts and special keys.

```bash
# Press Home button
python3 sim-keyboard.py home

# Lock screen
python3 sim-keyboard.py lock

# Toggle software keyboard
python3 sim-keyboard.py keyboard

# Shake gesture
python3 sim-keyboard.py shake

# App switcher (double Home)
python3 sim-keyboard.py app-switcher

# Custom key with modifiers
python3 sim-keyboard.py --key "a" --modifiers "cmd,shift"
```

### System Features

#### sim-openurl.py
Open URLs or deep links.

```bash
# Open webpage
python3 sim-openurl.py --url "https://apple.com"

# Open Maps with query
python3 sim-openurl.py --url "maps://?q=coffee+near+me"

# Custom app deep link
python3 sim-openurl.py --url "myapp://path/to/screen"
```

#### sim-location.py
Set simulated GPS location.

```bash
# Set to San Francisco
python3 sim-location.py --lat 37.7749 --lon -122.4194

# Set to New York
python3 sim-location.py --lat 40.7128 --lon -74.0060

# Clear simulated location
python3 sim-location.py --clear
```

#### sim-appearance.py
Set light or dark mode.

```bash
python3 sim-appearance.py dark
python3 sim-appearance.py light
```

## Automation Workflow Example

Here's a typical workflow to automate UI testing:

```bash
# 1. Ensure simulator is running
python3 sim-list.py --booted
# If none booted:
python3 sim-boot.py --name "iPhone 15"

# 2. Launch the app
python3 sim-launch.py --bundle-id com.example.myapp

# 3. Wait for app to load, then screenshot
sleep 2
python3 sim-screenshot.py --output /tmp/step1.png
# View /tmp/step1.png with Read tool

# 4. Based on screenshot, tap the login button (e.g., at 200,500)
python3 sim-tap.py --x 200 --y 500

# 5. Screenshot to see login form
python3 sim-screenshot.py --output /tmp/step2.png
# View /tmp/step2.png

# 6. Tap email field and type
python3 sim-tap.py --x 200 --y 300
python3 sim-type.py --text "user@example.com"

# 7. Tap password field and type
python3 sim-tap.py --x 200 --y 400
python3 sim-type.py --text "password123"

# 8. Tap login button
python3 sim-tap.py --x 200 --y 550

# 9. Verify result
sleep 2
python3 sim-screenshot.py --output /tmp/step3.png
# View /tmp/step3.png to confirm login success
```

## Coordinate System

- Coordinates are in **screen points** (not pixels)
- Origin (0, 0) is **top-left** of the simulator screen
- Typical iPhone dimensions:
  - iPhone SE: 375 x 667 points
  - iPhone 14/15: 390 x 844 points
  - iPhone 14/15 Pro Max: 430 x 932 points
- When viewing screenshots, estimate coordinates based on element position

## Troubleshooting

### "No booted simulator found"
Boot a simulator first:
```bash
python3 sim-boot.py --name "iPhone 15"
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
- Use `sim-list.py --booted` to see all running simulators
