---
name: sim-statusbar
description: Override the iOS simulator status bar for clean screenshots. Set custom time, battery level, signal bars, and carrier name. Perfect for App Store screenshots.
---

# Simulator Status Bar

Override the status bar in an iOS simulator.

## Usage

```bash
# Set custom values
scripts/sim-statusbar.py --udid SIMULATOR_UDID [options]

# Clear overrides
scripts/sim-statusbar.py --udid SIMULATOR_UDID --clear
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--udid` | Yes | Simulator UDID |
| `--time` | No | Custom time (e.g., "9:41") |
| `--battery` | No | Battery level (0-100) |
| `--battery-state` | No | charged, charging, or discharging |
| `--wifi` | No | WiFi signal bars (0-3) |
| `--cellular` | No | Cellular signal bars (0-4) |
| `--carrier` | No | Carrier name |
| `--clear` | No | Clear all overrides |

## Examples

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

## Output

```json
{
  "success": true,
  "message": "Status bar overrides applied",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

## Notes

- The time "9:41" is Apple's traditional marketing time
- Overrides persist until cleared or simulator is erased
- Useful for creating consistent App Store screenshots
