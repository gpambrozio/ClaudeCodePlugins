# iOS Simulator Plugin

The `iOSSimulator` plugin is available for controlling iOS Simulators.

## When to Use

Use the `ios-simulator` skill whenever you need to:
- List, boot, or shutdown iOS Simulators
- Take screenshots of the simulator (you can view these!)
- Launch or terminate apps
- Automate UI interactions (tap, swipe, type)
- Set device location or appearance (dark/light mode)
- Open URLs or deep links

## Quick Reference

All scripts are in the plugin's `skills/ios-simulator/scripts/` directory:

| Script | Purpose |
|--------|---------|
| `sim-list.py` | List simulators |
| `sim-boot.py` | Boot a simulator |
| `sim-screenshot.py` | Take screenshot |
| `sim-tap.py` | Tap at coordinates |
| `sim-type.py` | Type text |
| `sim-swipe.py` | Swipe gesture |
| `sim-launch.py` | Launch app |
| `sim-openurl.py` | Open URL |

## Screenshot-Based Workflow

Since you can view images, the recommended workflow is:
1. Take a screenshot with `sim-screenshot.py`
2. View the screenshot with the Read tool
3. Identify UI elements and their approximate coordinates
4. Use `sim-tap.py` to interact with those elements
5. Repeat as needed
