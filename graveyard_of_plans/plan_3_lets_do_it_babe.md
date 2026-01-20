# Plan 3: TUI Enhancement Features

## Feature 1: Two-Pane Viewer Title Differentiation

### Current State
The comparison screen (`scripts/tui/views/comparison_screen.py`) already has panel headers:
- Left panel: "ORIGINAL JSONL"
- Right panel: "PARSER_FINALE OUTPUT"

These use the `.panel-header` CSS class with:
- Docked to top, height of 3 lines
- Background: `$surface`
- Bold text, centered, with bottom border

### Questions to Clarify

1. **Are the current titles not visible enough?** If so, possible enhancements:
   - Add distinct background colors (e.g., blue for original, green for parsed)
   - Increase font contrast or add icons/symbols
   - Make headers larger or more prominent

2. **Should the titles be renamed?** Current options vs alternatives:
   - "ORIGINAL JSONL" → "Original Record", "Source Data", "Raw Input"
   - "PARSER_FINALE OUTPUT" → "Parsed Content", "Processed Result", "Output"

3. **Should titles include dynamic info?** Such as:
   - Record index/UUID
   - File name being viewed
   - Field count or data size

### Decision
**Both visual distinction AND clearer labels** - The current headers exist but aren't visible/prominent enough for users.

### Proposed Implementation

#### 1. Clearer Labels
Update the Static text in `compose()`:
- Left panel: "ORIGINAL JSONL" → **"Original Record"** (or "Source Data")
- Right panel: "PARSER_FINALE OUTPUT" → **"Parsed Output"** (or "Processed Result")

#### 2. Visual Distinction with Colors
Add distinct background colors to each panel header so they're immediately recognizable:

```css
#left-panel .panel-header {
    background: $primary;          /* Blue-ish for original */
    color: $text;
}

#right-panel .panel-header {
    background: $success;          /* Green-ish for parsed/processed */
    color: $text;
}
```

Alternative color schemes to consider:
- Blue (original) / Green (parsed) - implies "before/after" transformation
- Orange (original) / Cyan (parsed) - high contrast, distinct
- Use border accents instead of full background color

#### 3. Files to Modify
- `scripts/tui/views/comparison_screen.py`
  - Update CSS for `.panel-header` or add `#left-panel .panel-header` / `#right-panel .panel-header` rules
  - Update Static widget text in `compose()` method (lines 135, 138)

---

## Additional Features (add below)

<!-- Add more features here -->
