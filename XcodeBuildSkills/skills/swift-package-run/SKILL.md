---
name: swift-package-run
description: Run an executable target from a Swift Package using `swift run`. Supports foreground execution with timeout, background execution, and passing arguments to the executable.
---

# Swift Package Run

Run Swift package executables with `swift run`.

## Usage

```bash
scripts/swift-package-run.py --package-path /path/to/package [options]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--package-path` | Yes | Path to the Swift package root directory |
| `--executable` | No | Name of executable to run (defaults to package name) |
| `--configuration` | No | Build configuration: `debug` (default) or `release` |
| `--arguments` | No | Arguments to pass to the executable |
| `--timeout` | No | Timeout in seconds (default: 30, max: 300) |
| `--background` | No | Run in background and return immediately |
| `--parse-as-library` | No | Add `-parse-as-library` flag for `@main` support |

## Examples

```bash
# Run default executable
scripts/swift-package-run.py --package-path /path/to/MyPackage

# Run specific executable
scripts/swift-package-run.py --package-path /path/to/MyPackage --executable mytool

# Run with arguments
scripts/swift-package-run.py --package-path /path/to/MyPackage --arguments --verbose --config test.json

# Run in background
scripts/swift-package-run.py --package-path /path/to/MyPackage --background

# Run release build with longer timeout
scripts/swift-package-run.py --package-path /path/to/MyPackage --configuration release --timeout 60
```

## Output

Foreground execution:
```json
{
  "success": true,
  "message": "Execution completed",
  "package_path": "/path/to/MyPackage",
  "output": "Program output..."
}
```

Background execution:
```json
{
  "success": true,
  "message": "Process started in background",
  "pid": 12345,
  "package_path": "/path/to/MyPackage",
  "executable": "mytool",
  "hint": "Use swift-package-stop.py --pid <pid> to stop the process"
}
```
