---
allowed-tools: mcp__plugin_XcodeBuildTools_sosumi__searchAppleDocumentation, mcp__plugin_XcodeBuildTools_sosumi__fetchAppleDocumentation
argument-hint: <file-path>
description: Review SwiftUI file for deprecated modifiers and suggest modern alternatives
---

# SwiftUI Modernization Review

Review the SwiftUI code in $ARGUMENTS and perform a comprehensive analysis using Apple's latest documentation.

## Your Task

### Phase 1: Identify Deprecated Modifiers
1. First, use mcp__plugin_XcodeBuildTools_sosumi__searchAppleDocumentation to search for each SwiftUI modifier used in the file
2. Check if any modifiers are marked as deprecated in Apple's documentation
3. For each deprecated modifier found:
   - Note the deprecation details
   - Search for and fetch the recommended replacement
   - Provide the modern alternative with code examples

### Phase 2: Find Better Modern Alternatives
1. Examine each SwiftUI modifier and API pattern in the code
2. Search Apple's documentation for newer, more efficient alternatives that achieve the same result
3. Focus on:
   - Modifiers that have been superseded by simpler APIs (e.g., `.cornerRadius()` → `.clipShape()` with RoundedRectangle)
   - Complex modifier chains that can be simplified with newer combined modifiers
   - Layout approaches that could use newer container views or modifiers
   - Observation patterns that could use newer @Observable or other modern patterns

### Phase 3: SwiftUI Best Practices Analysis
1. Review the overall SwiftUI implementation for:
   - Anti-patterns or common mistakes
   - Performance issues (unnecessary re-renders, inefficient state management)
   - Accessibility concerns
   - iOS/macOS version compatibility issues
2. Search Apple's Human Interface Guidelines and SwiftUI documentation for best practices related to the patterns found
3. Suggest improvements aligned with Apple's latest recommendations

## Output Format

Provide your findings in the following structure:

### Deprecated Modifiers Found
List each deprecated modifier with:
- Current usage in the code
- Deprecation details from Apple docs
- Recommended replacement with code example

### Modernization Opportunities
List each opportunity to use newer APIs:
- Current implementation
- Modern alternative
- Benefits of the change
- Code example of the updated approach

### SwiftUI Best Practice Issues
List any issues found:
- Description of the issue
- Why it's problematic
- Recommended fix with code example

### Summary
- Total deprecated modifiers: X
- Total modernization opportunities: Y
- Priority recommendations for immediate fixes

Remember to verify all suggestions against Apple's official documentation using the MCP server to ensure accuracy and provide links to relevant documentation where helpful.
