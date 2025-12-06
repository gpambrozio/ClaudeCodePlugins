---
name: erase-simulator
description: Erase (factory reset) an iOS simulator, removing all installed apps and data. Use to reset a simulator to a clean state.
---

# Erase Simulator

Factory reset an iOS simulator.

## Usage

```bash
scripts/erase-simulator.py --udid SIMULATOR_UDID [--shutdown-first]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--udid` | Yes | Simulator UDID to erase |
| `--shutdown-first` | No | Shutdown simulator before erasing |

## Examples

```bash
# Erase a shutdown simulator
scripts/erase-simulator.py --udid XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

# Shutdown and erase
scripts/erase-simulator.py --udid XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX --shutdown-first
```

## Output

```json
{
  "success": true,
  "message": "Simulator erased successfully",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "note": "All data and settings have been reset to factory defaults"
}
```

## What Gets Erased

- All installed apps
- App data and preferences
- Photos, contacts, and other user data
- Login credentials and keychain items
- Custom settings and configurations

## Notes

- The simulator must be shutdown before erasing
- Use `--shutdown-first` to automatically shutdown a booted simulator
- The simulator device itself is not deleted, only its contents
