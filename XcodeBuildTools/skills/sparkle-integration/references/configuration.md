# Sparkle Configuration Files

## Package.swift

Add Sparkle dependency:

```swift
// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "YourAppPackage",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "YourAppFeature", targets: ["YourAppFeature"]),
    ],
    dependencies: [
        .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.6.0"),
    ],
    targets: [
        .target(
            name: "YourAppFeature",
            dependencies: [
                .product(name: "Sparkle", package: "Sparkle"),
            ]
        ),
    ]
)
```

## Info.plist

Add these keys:

```xml
<key>SUFeedURL</key>
<string>https://YOUR_USERNAME.github.io/YOUR_REPO/appcast.xml</string>
<key>SUPublicEDKey</key>
<string>YOUR_PUBLIC_KEY_FROM_generate_keys</string>
```

## Entitlements

**Important:** Create separate entitlement files for Debug and Release builds.

### Release Entitlements (YourApp.entitlements)

Used for Release builds - does NOT include `disable-library-validation` for security:

```xml
<!-- Required for downloading updates -->
<key>com.apple.security.network.client</key>
<true/>
```

### Debug Entitlements (YourApp.Debug.entitlements)

Used for Debug builds only - includes `disable-library-validation` because Sparkle.framework
has a different Team ID when loaded via SPM:

```xml
<!-- Required for downloading updates -->
<key>com.apple.security.network.client</key>
<true/>

<!-- DEBUG ONLY: Required because Sparkle.framework has different Team ID via SPM -->
<!-- See: https://sparkle-project.org/documentation/#1-add-the-sparkle-framework-to-your-project -->
<key>com.apple.security.cs.disable-library-validation</key>
<true/>
```

### Xcode Project Configuration

Update the project to use the correct entitlements per configuration:

1. In Xcode, select your target → Build Settings
2. Search for "Code Signing Entitlements"
3. Expand the setting to show Debug/Release rows
4. Set Debug to: `Config/YourApp.Debug.entitlements`
5. Set Release to: `Config/YourApp.entitlements`

Or in `.xcodeproj/project.pbxproj`, ensure the Debug configuration uses the Debug entitlements:
```
CODE_SIGN_ENTITLEMENTS = Config/YourApp.Debug.entitlements;  /* Debug */
CODE_SIGN_ENTITLEMENTS = Config/YourApp.entitlements;        /* Release */
```

## XCConfig

Add to `Shared.xcconfig`:

```
MARKETING_VERSION = 1.0
CURRENT_PROJECT_VERSION = 1
LD_RUNPATH_SEARCH_PATHS = $(inherited) @executable_path/../Frameworks
```

## Export Options (Scripts/export-options.plist)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>developer-id</string>
    <key>teamID</key>
    <string>YOUR_TEAM_ID</string>
    <key>signingStyle</key>
    <string>automatic</string>
    <key>destination</key>
    <string>export</string>
</dict>
</plist>
```
