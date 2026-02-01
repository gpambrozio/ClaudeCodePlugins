# Sparkle Swift Code Examples

## UpdaterController

Create `Services/UpdaterController.swift` in your feature package:

```swift
import Combine
import Foundation
import Sparkle

/// A controller class that manages the Sparkle updater for the application.
/// This class wraps SPUStandardUpdaterController and provides SwiftUI-friendly bindings.
///
/// Uses @Observable (Swift's modern observation) instead of ObservableObject/Combine.
/// Sparkle's KVO-based properties still require Combine for observation.
@Observable
@MainActor
public final class UpdaterController {
    private let updaterController: SPUStandardUpdaterController
    private var cancellable: AnyCancellable?

    /// Whether the user can check for updates (not currently checking)
    public private(set) var canCheckForUpdates = false

    /// The date of the last update check, if any
    public var lastUpdateCheckDate: Date? {
        updaterController.updater.lastUpdateCheckDate
    }

    public init() {
        self.updaterController = SPUStandardUpdaterController(
            startingUpdater: true,
            updaterDelegate: nil,
            userDriverDelegate: nil
        )
        // Observe canCheckForUpdates using Combine (Sparkle uses KVO internally)
        // Store the cancellable to keep the subscription alive
        self.cancellable = updaterController.updater.publisher(for: \.canCheckForUpdates)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] value in
                self?.canCheckForUpdates = value
            }
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
    private let updaterController: UpdaterController

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

In your main app file (uses `@State` with `@Observable`, not `@StateObject`):

```swift
import SwiftUI
import YourAppFeature

@main
struct YourApp: App {
    @State private var updaterController = UpdaterController()

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
