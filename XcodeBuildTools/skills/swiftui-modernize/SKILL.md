---
name: swiftui-modernize
description: Use when reviewing SwiftUI files for deprecated APIs, modern alternatives, Apple docs-backed modernization, or SwiftUI best practices.
---

# SwiftUI Modernize

Review the requested SwiftUI file or files for deprecated modifiers, modern API alternatives, and SwiftUI best practices.

## Workflow

1. Identify the SwiftUI modifiers, property wrappers, view containers, and API patterns in the target file.
2. Use available Apple documentation search/fetch tools to verify deprecations and recommended replacements.
3. If Apple documentation tools are unavailable, state that live documentation verification was unavailable and keep suggestions conservative.
4. Check for:
   - Deprecated modifiers or APIs
   - Superseded modifiers, such as simpler shape, layout, observation, or presentation APIs
   - Complex modifier chains that newer combined modifiers can simplify
   - Layout approaches that could use newer containers or modifiers
   - Observation patterns that could use modern `@Observable` or related APIs
   - Accessibility, performance, and platform compatibility issues

## Output Format

### Deprecated Modifiers Found

For each item:

- Current usage
- Deprecation detail
- Recommended replacement
- Code example
- Documentation link when available

### Modernization Opportunities

For each item:

- Current implementation
- Modern alternative
- Benefit
- Code example

### SwiftUI Best Practice Issues

For each item:

- Issue
- Why it matters
- Recommended fix

### Summary

Include counts for deprecated modifiers and modernization opportunities, then list priority recommendations.
