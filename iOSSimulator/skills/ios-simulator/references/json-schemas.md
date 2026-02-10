# JSON Output Schemas

All scripts output JSON to stdout. Every response includes a `success` boolean field.

## Standard Responses

### Success Response
```json
{
  "success": true,
  "message": "Description of what was done",
  "udid": "SIMULATOR-UDID"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Description of what went wrong. Helpful hint if available.",
  "error_category": "category_name"
}
```

### Error Categories

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

**Note:** Some "errors" are actually success conditions (marked above). For example, booting an already-booted simulator returns `"success": true` with the note about current state.

## Script-Specific Schemas

### sim-list.py
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

### sim-boot.py
```json
{
  "success": true,
  "message": "Simulator booted successfully",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "name": "iPhone 15",
  "runtime": "iOS-17-0",
  "boot_time_seconds": 4.2,
  "ready": true
}
```

### sim-clipboard.py
```json
{
  "success": true,
  "message": "Text copied to clipboard",
  "text": "Hello, World!",
  "length": 13,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

### sim-create.py
```json
{
  "success": true,
  "message": "Created iPhone 15 Pro (iOS 18.0)",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "name": "iPhone 15 Pro",
  "device_type": "iPhone 15 Pro",
  "device_type_id": "com.apple.CoreSimulator.SimDeviceType.iPhone-15-Pro",
  "runtime": "iOS 18.0",
  "runtime_id": "com.apple.CoreSimulator.SimRuntime.iOS-18-0"
}
```

### sim-delete.py
```json
{
  "success": true,
  "message": "Deleted simulator iPhone 15",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "name": "iPhone 15"
}
```

### sim-erase.py
```json
{
  "success": true,
  "message": "Erased simulator iPhone 15 (factory reset)",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "name": "iPhone 15"
}
```

### sim-screenshot.py
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
**Note:** The `screen.scale` field is needed to convert pixel coordinates from screenshots to point coordinates for `sim-tap.py`. Divide pixel coordinates by `scale`.

### sim-tap.py
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

### sim-swipe.py
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

### sim-type.py
```json
{
  "success": true,
  "message": "Cleared and typed 12 characters",
  "text_length": 12,
  "cleared": true,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

### sim-keyboard.py
```json
{
  "success": true,
  "message": "Sent combo: cmd+a",
  "combo": "cmd+a",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

### sim-launch.py
```json
{
  "success": true,
  "message": "Launched com.apple.Preferences",
  "bundle_id": "com.apple.Preferences",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "pid": 12345
}
```

### sim-location.py
```json
{
  "success": true,
  "message": "Location set",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

### sim-device-info.py
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

### sim-describe-ui.py (nested format)
```json
{
  "success": true,
  "simulator": {"udid": "...", "name": "iPhone 15"},
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

### sim-describe-ui.py (flat format)
```json
{
  "success": true,
  "simulator": {"udid": "...", "name": "iPhone 15"},
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
```

### sim-describe-ui.py (find mode)
```json
{
  "success": true,
  "count": 2,
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

### sim-record-video.py
```json
{
  "success": true,
  "message": "Recording completed",
  "output": "/tmp/demo.mp4",
  "size_bytes": 1234567,
  "codec": "h264"
}
```

### sim-statusbar.py
```json
{
  "success": true,
  "message": "Status bar overrides applied",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

### sim-visual-diff.py
```json
{
  "success": true,
  "passed": true,
  "verdict": "PASS",
  "difference_percentage": 0.23,
  "threshold_percentage": 1.0,
  "different_pixels": 2650,
  "total_pixels": 1149984,
  "dimensions": [1170, 2532],
  "baseline": "/tmp/baseline.png",
  "current": "/tmp/current.png",
  "artifacts": {
    "diff_image": "/tmp/diff/diff.png",
    "side_by_side": "/tmp/diff/side-by-side.png"
  }
}
```

### sim-screen-map.py
```json
{
  "success": true,
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "total_elements": 45,
  "interactive_elements": 7,
  "buttons": ["Login", "Cancel", "Forgot Password"],
  "text_fields": [
    {"label": "Email", "type": "text", "has_value": false},
    {"label": "Password", "type": "secure", "has_value": false}
  ],
  "navigation": {"nav_title": "Sign In"},
  "hints": ["Login screen detected - look for text fields for credentials"]
}
```

### sim-privacy.py
```json
{
  "success": true,
  "action": "grant",
  "bundle_id": "com.example.myapp",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "message": "Grant camera, photos for com.example.myapp",
  "results": [
    {"service": "camera", "description": "Camera access", "success": true},
    {"service": "photos", "description": "Photos library access", "success": true}
  ]
}
```

### sim-push.py
```json
{
  "success": true,
  "message": "Push notification sent to com.example.myapp",
  "bundle_id": "com.example.myapp",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "payload": {
    "aps": {
      "alert": {"title": "New Message", "body": "Hello!"},
      "sound": "default"
    }
  }
}
```

### sim-logs.py
```json
{
  "success": true,
  "bundle_id": "com.example.myapp",
  "udid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "statistics": {
    "total_lines": 142,
    "errors": 2,
    "warnings": 5,
    "info": 38,
    "debug": 97
  },
  "errors": ["2025-01-15 10:30:01 MyApp[1234] Error: Failed to load resource"],
  "warnings": ["2025-01-15 10:30:02 MyApp[1234] Warning: Deprecated API usage"]
}
```
