---
name: swift-code-analysis
description: Use when reviewing Swift code for architecture, memory, SwiftUI, dead code, optional handling, or code quality issues.
---

# Swift Code Analysis

Perform a comprehensive Swift code review for the current project or requested files.

## Review Areas

- Architecture patterns such as MVC, MVVM, VIPER, reducers, coordinators, or feature modules
- Common Swift anti-patterns and code smells
- Memory management issues, retain cycles, and strong reference risks
- SwiftUI best practice violations
- Unused imports and dead code
- Force unwraps, implicitly unwrapped optionals, and weak optional handling
- Protocol conformance or abstraction opportunities

## Output

Report findings with:

- File and line reference when available
- Severity: critical, warning, or suggestion
- Concrete reason the issue matters
- A targeted fix or next step

Prioritize behavior, correctness, maintainability, and user-visible risk over broad style commentary.
