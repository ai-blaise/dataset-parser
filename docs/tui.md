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
uv run python -m scripts.tui.app <path> [options]
```

The TUI accepts either a single file or a directory containing data files.

### Options

| Option | Description |
|--------|-------------|
| `-O, --output-dir` | Output directory for export operations (default: parsed_datasets) |

### Single File Mode

```bash
# JSONL file
uv run python -m scripts.tui.app dataset/conversations.jsonl

# Parquet file
uv run python -m scripts.tui.app dataset/train-00000-of-00001.parquet

# JSON file
uv run python -m scripts.tui.app dataset/data.json
```

### Directory Mode

When you pass a directory, the TUI displays a file picker showing all supported data files:

```bash
# Open a directory of data files
uv run python -m scripts.tui.app dataset/

# The file picker shows all .jsonl, .json, .parquet, and .pq files
uv run python -m scripts.tui.app /path/to/data/directory
```

In directory mode:
- Select a file from the list to view its records
- Press `ESC` or `b` from the Record List to return to the file picker
- File sizes are displayed for easy identification

## Keybindings

### Global

| Key | Action |
|-----|--------|
| `q` | Quit application |

### File List Screen (Directory Mode)

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate files |
| `Enter` | Open selected file |
| `P` | Export all files (processed) to output directory |
| `ESC` | Quit application |

### Record List Screen

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate records |
| `Enter` | Open comparison view |
| `ESC` / `b` | Back to file list (directory mode) or quit |
| `X` | Export all records (processed) to output directory |

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
| `x` | Export current record (processed) to output directory |
| `↑/↓` | Navigate tree nodes |
| `Enter` | Expand/collapse node |

### Field Detail Modal

| Key | Action |
|-----|--------|
| `ESC` / `Enter` | Close modal |
| `q` | Quit application |

## Screens

### File List Screen (Directory Mode)

When you open a directory, the File List Screen displays all supported data files:

| Column | Description |
|--------|-------------|
| FILE NAME | Name of the data file |
| FORMAT | File format (JSONL, JSON, PARQUET) |
| SIZE | File size (B, KB, MB, GB) |

**Navigation:**

- Use arrow keys to move between files
- Press `Enter` to open the selected file
- Press `ESC` or `q` to quit

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

- **Left panel**: Original Record (blue header)
- **Right panel**: Parsed Output (green header)

Features:

- **Synchronized scrolling**: Both panels scroll together (toggle with `s`)
- **Synchronized expansion**: Expanding/collapsing nodes mirrors to other panel
- **Diff highlighting**: Shows changes between original and processed (toggle with `d`)
- **Hierarchical JSON tree**: Collapsible tree view of nested data
- **Field detail modal**: View full untruncated content (press `m`)

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

### Browsing a Directory

1. Launch the TUI with a directory path
2. Use arrow keys to navigate the file list
3. Press `Enter` to open a file
4. Press `ESC` or `b` from the record list to return to the file picker

### Browsing Records

1. Launch the TUI with your dataset file (or select from directory)
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

### Exporting Data

The TUI can export processed records to files. Exports go to the output directory specified by `--output-dir` (default: `parsed_datasets/`).

**Export all records (batch):**

1. From the Record List screen, press `X` (Shift+x)
2. All records will be processed and exported
3. Output file: `{output_dir}/{source_filename}_parsed.json`

**Export single record:**

1. From the Comparison Screen, press `x`
2. The current processed record will be exported
3. Output file: `{output_dir}/{source_filename}_record_{index}_parsed.json`

**Export all files in directory:**

1. From the File List screen (directory mode), press `P` (Shift+p)
2. All files in the directory will be processed and exported
3. Each file creates: `{output_dir}/{filename}_parsed.json`

**Export Progress Screen:**

When exporting, a progress screen appears showing:
- Current file/record being processed
- Progress count (e.g., "3 / 10 completed")
- Completion message with output path
- Auto-dismisses after export completes

**Example:**

```bash
# Export all files in a directory
uv run python -m scripts.tui.app dataset/ -O my_exports/
# Then press P to export all files to my_exports/

# Export single file's records
uv run python -m scripts.tui.app dataset/train.jsonl -O my_exports/
# Then press X to export all records to my_exports/train_parsed.json
```

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

### Caching

Records are cached after the first load to improve navigation performance:

- Moving between Record List and Comparison Screen doesn't reload the file
- Cache is per-file and session-scoped
- Large files benefit significantly from caching

### Memory Safety

The TUI includes multiple safeguards to prevent crashes on deeply nested or large data:

| Limit | Value | Purpose |
|-------|-------|---------|
| Tree display depth | 100 | Prevents stack overflow in recursive rendering |
| Diff calculation depth | 100 | Prevents stack overflow in comparison |
| Expand/collapse depth | 50 | Limits recursive operations |
| String processing | 10,000 chars | Prevents memory issues with huge strings |
| Display truncation | 50 chars | Keeps UI responsive |

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
