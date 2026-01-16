# TUI Application Guide

The TUI (Terminal User Interface) provides an interactive way to browse and analyze JSONL datasets.

## Running the TUI

```bash
uv run python -m scripts.tui.app <file>
```

Example:

```bash
uv run python -m scripts.tui.app dataset/conversations.jsonl
```

## Keybindings

| Key | Action |
|-----|--------|
| `Enter` | View full record details (Messages, Tools, Metadata tabs) |
| `f` | Show field detail modal for current cell |
| `q` | Quit application |
| `ESC` | Close modal / Go back to list |
| `Tab` | Switch tabs in detail view |
| `Arrow keys` | Navigate cells in the table |

## Screens

### Record List Screen

The main screen displays all records in a table format:

| Column | Description |
|--------|-------------|
| IDX | Record index (0-based) |
| UUID | Truncated unique identifier |
| MSGS | Number of messages |
| TOOLS | Number of tool definitions |
| LICENSE | License type |
| USED_IN | Usage contexts |
| RSN | Reasoning flag ("on" or "-") |
| PREVIEW | First user message preview |

**Navigation:**

- Use arrow keys to move between cells
- Press `Enter` to view full record details
- Press `f` to see detailed information for the current cell

### Comparison Screen

When you select a record, you see a side-by-side comparison:

- **Left panel**: Original record
- **Right panel**: Processed record (parser finale output)

Features:

- Synchronized scrolling between panels
- Diff highlighting shows changes
- Hierarchical JSON tree view

### Field Detail Modal

Press `f` on any cell to see detailed information:

| Field | Detail View Shows |
|-------|-------------------|
| IDX | Record index with navigation hint |
| UUID | Full UUID (untruncated) |
| MSGS | Message count breakdown by role |
| TOOLS | Scrollable list of tool names and descriptions |
| LICENSE | Full license name |
| USED_IN | Complete list of usage contexts |
| RSN | Reasoning status and count of messages with reasoning_content |
| PREVIEW | Full first user message content |

## Workflow

### Browsing Records

1. Launch the TUI with your dataset file
2. Use arrow keys to navigate the record list
3. Press `f` to preview fields without leaving the list
4. Press `Enter` to view full record details

### Analyzing Differences

1. Select a record with `Enter`
2. Compare original (left) vs processed (right) panels
3. Look for diff highlighting to identify changes
4. Press `ESC` to return to the list

### Inspecting Tools

1. Navigate to a record with tools (TOOLS column > 0)
2. Press `f` on the TOOLS cell
3. Scroll through the tool names and descriptions
4. Press `ESC` to close the modal

## Tips

### Finding Records with Tools

Look at the TOOLS column - records with `0` have no tool definitions.

### Checking Reasoning Status

The RSN column shows "on" for records with reasoning enabled, "-" otherwise.

### Quick Preview

Use the PREVIEW column to see the first user message at a glance without opening the record.

### Large Datasets

The TUI loads records efficiently, so large datasets are supported. Use the MSGS column to identify conversation length before diving in.

## Visual Elements

### Diff Highlighting

In the comparison view, changes are highlighted:

- **Added content**: Shown in the processed panel only
- **Removed content**: Shown in the original panel only (assistant messages)
- **Changed content**: Highlighted in both panels

### JSON Tree

Records are displayed as collapsible trees:

- Objects show their keys
- Arrays show their indices
- Primitives show their values
- Nested structures are indented
