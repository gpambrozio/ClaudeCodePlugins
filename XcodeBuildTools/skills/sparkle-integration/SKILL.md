---
name: sparkle-integration
description: Integrate Sparkle 2.x auto-update framework into macOS apps. Use when adding auto-update functionality for macOS applications.
---

# Sparkle Auto-Update Integration

Integrate Sparkle 2.x into macOS apps with workspace + SPM architecture, release automation, and GitHub Pages hosting.

## Prerequisites

```bash
brew install gh create-dmg sparkle
gh auth login
```

## Integration Steps

### 1. Add Sparkle to Package.swift

Add dependency: `.package(url: "https://github.com/sparkle-project/Sparkle", from: "2.6.0")`

See [references/configuration.md](references/configuration.md) for full Package.swift example.

### 2. Create Swift Code

Create `UpdaterController` and `CheckForUpdatesView`. See [references/swift-code.md](references/swift-code.md) for complete implementations.

### 3. Generate EdDSA Keys

```bash
generate_keys
```

Copy the public key output for Info.plist. Private key is stored in Keychain.

### 4. Configure Project Files

Add to Info.plist:
- `SUFeedURL`: `https://USERNAME.github.io/REPO/appcast.xml`
- `SUPublicEDKey`: Your public key from step 3

Add entitlements (create separate files for Debug/Release):
- `com.apple.security.network.client`: true (both)
- `com.apple.security.cs.disable-library-validation`: true (DEBUG ONLY - security risk in Release)

Add to xcconfig:
- `LD_RUNPATH_SEARCH_PATHS = $(inherited) @executable_path/../Frameworks`

See [references/configuration.md](references/configuration.md) for complete examples.

### 5. Set Up Release Script

Copy [scripts/release.sh](scripts/release.sh) to your project's `Scripts/` directory.

Customize the configuration section at the top:
- `WORKSPACE`, `SCHEME`, `APP_NAME`
- `GITHUB_REPO`
- `TEAM_ID`

```bash
chmod +x Scripts/release.sh
```

### 6. Set Up GitHub Pages

1. Go to repo Settings → Pages
2. Source: Deploy from branch
3. Branch: main, Folder: /docs
4. Save

### 7. Set Up Notarization

```bash
xcrun notarytool store-credentials "notarytool-profile" \
    --apple-id "your@email.com" \
    --team-id "YOUR_TEAM_ID"
```

## Usage

```bash
./Scripts/release.sh                    # Full release
./Scripts/release.sh --skip-notarize    # Skip notarization
./Scripts/release.sh --local-signing    # Local testing
```

## Critical: Version Numbers

`sparkle:version` MUST be the build number (CFBundleVersion), NOT marketing version.

```xml
<!-- Correct -->
<sparkle:version>7</sparkle:version>
<sparkle:shortVersionString>1.6</sparkle:shortVersionString>

<!-- Wrong - causes "no update found" -->
<sparkle:version>1.6</sparkle:version>
```

See [references/troubleshooting.md](references/troubleshooting.md) for common issues.

## Directory Structure

```
YourApp/
├── YourApp.xcworkspace/
├── YourApp/
│   ├── Info.plist              # SUFeedURL, SUPublicEDKey
│   └── YourApp.entitlements
├── Config/Shared.xcconfig      # MARKETING_VERSION, CURRENT_PROJECT_VERSION
├── YourAppPackage/
│   ├── Package.swift           # Sparkle dependency
│   └── Sources/YourAppFeature/
│       ├── Services/UpdaterController.swift
│       └── Views/CheckForUpdatesView.swift
├── Scripts/
│   ├── release.sh
│   └── export-options.plist
└── docs/appcast.xml            # Auto-generated
```
