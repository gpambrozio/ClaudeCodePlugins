# Sparkle Troubleshooting

## Critical: Version Numbers

**The most common Sparkle mistake.** The `sparkle:version` in appcast MUST be the **build number** (`CFBundleVersion`), NOT the marketing version.

**Correct:**
```xml
<sparkle:version>7</sparkle:version>
<sparkle:shortVersionString>1.6</sparkle:shortVersionString>
```

**Wrong:**
```xml
<sparkle:version>1.6</sparkle:version>
```

Sparkle compares CFBundleVersion numerically. "1.6" becomes "1", which is less than "7".

## Common Issues

### "No update found" when there should be one

Check that `sparkle:version` in appcast.xml uses build numbers, not marketing versions.

### Signature verification failed

Ensure `SUPublicEDKey` in Info.plist matches the key from `generate_keys`.

### Notarization fails

- Verify app-specific password is correct
- Check Team ID matches Developer ID certificate
- Ensure all binaries in app bundle are signed

### Sparkle framework not found at runtime

Add to xcconfig:
```
LD_RUNPATH_SEARCH_PATHS = $(inherited) @executable_path/../Frameworks
```

### Library validation error (Debug builds only)

This error occurs in **Debug builds** because Sparkle.framework has a different Team ID when loaded via SPM.

**Solution:** Create separate entitlement files:

1. `YourApp.Debug.entitlements` - includes `disable-library-validation`:
```xml
<key>com.apple.security.cs.disable-library-validation</key>
<true/>
```

2. `YourApp.entitlements` - does NOT include it (for Release builds)

Configure Xcode to use the Debug entitlements for Debug configuration only.

**Security Note:** `disable-library-validation` allows loading libraries with different Team IDs, which is a security risk. Only use it for Debug builds.

## Testing Auto-Updates

1. Build version 1.0 (build 1) and install it
2. Bump to version 1.1 (build 2) and run release
3. Open the old version and click "Check for Updates..."
4. Sparkle should detect and offer the update
