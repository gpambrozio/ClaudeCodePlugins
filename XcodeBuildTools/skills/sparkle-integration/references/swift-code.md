# Sparkle Swift Code Examples

## UpdaterController

Create `Services/UpdaterController.swift` in your feature package:

```swift
import Foundation
import Sparkle

/// A controller class that manages the Sparkle updater for the application.
/// This class wraps SPUStandardUpdaterController and provides SwiftUI-friendly bindings.
@MainActor
public final class UpdaterController: ObservableObject {
    private let updaterController: SPUStandardUpdaterController

    /// Whether the user can check for updates (not currently checking)
    @Published public private(set) var canCheckForUpdates = false

    /// The date of the last update check, if any
    public var lastUpdateCheckDate: Date? {
        updaterController.updater.lastUpdateCheckDate
    }

    public init() {
        updaterController = SPUStandardUpdaterController(
            startingUpdater: true,
            updaterDelegate: nil,
            userDriverDelegate: nil
        )
        updaterController.updater.publisher(for: \.canCheckForUpdates)
            .assign(to: &$canCheckForUpdates)
    }

    public func checkForUpdates() {
        updaterController.checkForUpdates(nil)
    }

    public var automaticallyChecksForUpdates: Bool {
        get { updaterController.updater.automaticallyChecksForUpdates }
        set { updaterController.updater.automaticallyChecksForUpdates = newValue }
    }

    public var updateCheckInterval: TimeInterval {
        get { updaterController.updater.updateCheckInterval }
        set { updaterController.updater.updateCheckInterval = newValue }
    }

    public var automaticallyDownloadsUpdates: Bool {
        get { updaterController.updater.automaticallyDownloadsUpdates }
        set { updaterController.updater.automaticallyDownloadsUpdates = newValue }
    }
}
```

## CheckForUpdatesView

Create `Views/CheckForUpdatesView.swift`:

```swift
import SwiftUI

public struct CheckForUpdatesView: View {
    @ObservedObject private var updaterController: UpdaterController

    public init(updaterController: UpdaterController) {
        self.updaterController = updaterController
    }

    public var body: some View {
        Button("Check for Updates...") {
            updaterController.checkForUpdates()
        }
        .disabled(!updaterController.canCheckForUpdates)
    }
}
```

## App Integration

In your main app file:

```swift
import SwiftUI
import YourAppFeature

@main
struct YourApp: App {
    @StateObject private var updaterController = UpdaterController()

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .commands {
            CommandGroup(after: .appInfo) {
                CheckForUpdatesView(updaterController: updaterController)
            }
        }
    }
}
```
