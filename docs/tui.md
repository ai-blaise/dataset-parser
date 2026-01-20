# TUI Application Guide

The TUI (Terminal User Interface) provides an interactive way to browse and analyze datasets containing AI conversation data. It supports multiple file formats including JSONL, JSON, and Parquet.

## Supported File Formats

| Format | Extensions | Description |
|--------|------------|-------------|
| JSONL | `.jsonl` | One JSON object per line (streaming) |
| JSON | `.json` | JSON array of objects |
| Parquet | `.parquet`, `.pq` | Apache Parquet columnar format |

The TUI automatically detects the file format from the extension. The title bar displays the detected format (e.g., "Dataset Viewer - data.parquet (parquet)").

### Schema Normalization

Different formats may use different field names. The TUI normalizes all records to a standard schema:

- Parquet files using `conversations` are converted to `messages`
- Parquet `trial_name` is used as `uuid` fallback
- Missing standard fields are assigned defaults

## Running the TUI

```bash
uv run python -m scripts.tui.app <file>
```

Examples:

```bash
# JSONL file
uv run python -m scripts.tui.app dataset/conversations.jsonl

# Parquet file
uv run python -m scripts.tui.app dataset/train-00000-of-00001.parquet

# JSON file
uv run python -m scripts.tui.app dataset/data.json
```

## Keybindings

### Global

| Key | Action |
|-----|--------|
| `q` | Quit application |

### Record List Screen

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate records |
| `Enter` | Open comparison view |

### Comparison Screen

| Key | Action |
|-----|--------|
| `ESC` / `b` | Back to record list |
| `Tab` | Switch panel focus |
| `←` | Focus left panel |
| `→` | Focus right panel |
| `s` | Toggle sync scroll |
| `d` | Toggle diff highlighting |
| `m` | Show field detail modal |
| `e` | Expand all nodes |
| `c` | Collapse all nodes |
| `↑/↓` | Navigate tree nodes |
| `Enter` | Expand/collapse node |

### Field Detail Modal

| Key | Action |
|-----|--------|
| `ESC` / `Enter` | Close modal |
| `q` | Quit application |

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
- Press `m` to see detailed information for the current cell

### Comparison Screen

When you select a record, you see a side-by-side comparison:

- **Left panel**: Original record
- **Right panel**: Processed record (parser finale output)

Features:

- Synchronized scrolling between panels
- Diff highlighting shows changes
- Hierarchical JSON tree view

### Field Detail Modal

Press `m` on any cell to see detailed information:

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
3. Press `m` to preview fields without leaving the list
4. Press `Enter` to view full record details

### Analyzing Differences

1. Select a record with `Enter`
2. Compare original (left) vs processed (right) panels
3. Look for diff highlighting to identify changes
4. Press `ESC` to return to the list

### Inspecting Tools

1. Navigate to a record with tools (TOOLS column > 0)
2. Press `m` on the TOOLS cell
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

For files over 100MB, the TUI shows a loading screen with progress:

- **JSONL/JSON**: Streams records one at a time to minimize memory usage
- **Parquet**: Uses PyArrow's efficient columnar access and metadata for record counts

### Format-Specific Notes

**Parquet files:**
- Record count is retrieved from file metadata (instant)
- Random access is efficient via row group seeking
- Nested structures (like conversations) are fully supported

**JSONL files:**
- Best for streaming large files
- Each line is parsed independently

**JSON files:**
- Entire file must be parsed at once
- Best for smaller datasets or exports

## Visual Elements

### Diff Highlighting

In the comparison view, changes are highlighted:

- **Changed content**: Assistant `content` fields (emptied in processed)
- **Removed content**: `reasoning_content` fields (dropped in processed)
- **Unchanged content**: All other fields (system, user, tool messages, tool_calls)

### JSON Tree

Records are displayed as collapsible trees:

- Objects show their keys
- Arrays show their indices
- Primitives show their values
- Nested structures are indented
