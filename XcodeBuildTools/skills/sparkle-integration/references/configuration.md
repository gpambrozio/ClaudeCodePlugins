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

Required entitlements:

```xml
<!-- Required for downloading updates -->
<key>com.apple.security.network.client</key>
<true/>

<!-- Required because Sparkle.framework has different Team ID via SPM -->
<key>com.apple.security.cs.disable-library-validation</key>
<true/>
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
