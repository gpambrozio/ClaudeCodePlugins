# Troubleshooting

## "No booted simulator found"
Boot a simulator first:
```bash
scripts/sim-list.py
scripts/sim-boot.py --name "iPhone 15"
```

## Taps not registering at correct position
- The coordinate translation includes estimated bezel offsets
- Take a screenshot and verify the visible area matches expectations
- Try adjusting coordinates slightly
- Check `sim-device-info.py` for the correct scale factor

## Text not typing
- Ensure a text field is focused by tapping on it first
- Try `--slow` flag for more reliable character-by-character input
- Use `--clear` to clear existing text before typing new text

## Quartz module not found
- The tap/swipe scripts require the `pyobjc-framework-Quartz` module
- This is usually pre-installed on macOS with Xcode
- Fallback to AppleScript will be used if Quartz is unavailable

## Screenshots show wrong simulator
- If multiple simulators are booted, specify `--udid` explicitly
- Use `scripts/sim-list.py --booted` to see all running simulators

## sim-describe-ui.py fails
- Requires `uv` for dependency management
- Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- The script auto-installs pyobjc dependencies on first run

## Simulator window not found (swipe/tap fails)
- Ensure Simulator.app is open and visible on screen
- The scripts auto-activate Simulator and set Point Accurate mode (Cmd+2)
- If using multiple displays, the simulator must be on a visible display

## Permission errors with privacy commands
- The simulator must be booted before granting/revoking permissions
- The app must be installed (use `sim-install.py` first)
- Use `--list` on `sim-privacy.py` to see supported services

## Push notifications not appearing
- The app must be installed on the simulator
- Ensure the bundle ID is correct
- The app should be configured to handle push notifications
