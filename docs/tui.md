# TUI Application Guide

The TUI provides an interactive way to browse and compare datasets. Currently optimized for AI conversation data, with dynamic schema detection for varying field structures. Supports JSONL, JSON, and Parquet formats.

## Supported File Formats

| Format | Extensions | Description |
|--------|------------|-------------|
| JSONL | `.jsonl` | One JSON object per line (streaming) |
| JSON | `.json` | JSON array of objects |
| Parquet | `.parquet`, `.pq` | Apache Parquet columnar format |

The TUI automatically detects the file format from the extension. The title bar displays the detected format (e.g., "Dataset Viewer - data.parquet (parquet)").

### Dynamic Schema Detection

The TUI automatically detects field mappings from your data:

**ID Field Detection** (priority order):
1. Known field names: `uuid`, `id`, `uid`, `example_id`, `trial_name`, `chat_id`, `conversation_id`
2. Values matching UUID format (8-4-4-4-12 hex pattern)

**Message Field Detection**:
- Looks for arrays containing objects with `role` or `content` keys
- If multiple candidates, selects the largest array

**Tool Field Detection**:
- Looks for arrays containing objects with `function` or `name` keys

**Schema Normalization**:
- Parquet `conversations` field is converted to `messages`
- Parquet `trial_name` is used as `uuid` fallback
- Missing standard fields are assigned defaults

**Raw Mode**: If no message field is detected, the TUI falls back to "raw mode" showing the original data without transformation.

## Running the TUI

```bash
uv run python -m scripts.tui.app <path> [options]
```

The TUI accepts either a single file or a directory containing data files.

### Options

| Option | Description |
|--------|-------------|
| `-O, --output-dir` | Output directory for export operations (default: parsed_datasets) |
| `-c, --compare` | Path to second dataset for side-by-side comparison |

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
- Select a file from the list to view its records (`ENTER`)
- Press `ESC` or `b` from the Record List to return to the file picker
- File sizes are displayed for easy identification

### Dataset Comparison Mode

Compare two datasets side-by-side without parser_finale transformation:

```bash
# Compare two individual files
uv run python -m scripts.tui.app dataset/train_v1.jsonl --compare dataset/train_v2.jsonl

# Compare two directories (file picker for each side)
uv run python -m scripts.tui.app dataset_a/ --compare dataset_b/

# Compare Parquet files
uv run python -m scripts.tui.app data/train-v1.parquet --compare data/train-v2.parquet
```

In comparison mode:
- **Single files**: Both files load directly, showing Dataset Comparison Screen
- **Directories**: File picker appears for each side, select files then press `ESC` to compare

**Record Matching:**
- Records are matched by UUID if both datasets have matching UUIDs
- Falls back to index-based matching if UUIDs differ or are missing

## Keybindings

### Global

| Key | Action |
|-----|--------|
| `q` | Quit application |

### Global Vim Navigation

All screens support vim-style navigation keybindings:

| Key | Action |
|-----|--------|
| `j` | Move cursor down (same as `↓`) |
| `k` | Move cursor up (same as `↑`) |
| `h` | Focus left panel (in dual-pane screens) |
| `l` | Focus right panel (in dual-pane screens) |
| `g` | Jump to first item |
| `G` | Jump to last item |

These work across all screens with DataTable, ListView, and Tree widgets.

### File List Screen (Directory Mode)

| Key | Action |
|-----|--------|
| `↑/↓` or `j/k` | Navigate files |
| `g` | Jump to first file |
| `G` | Jump to last file |
| `Enter` | Open selected file |
| `P` | Export all files (processed) to output directory |
| `ESC` | Quit application |

### Comparison Select Screen (Directory Comparison Mode)

| Key | Action |
|-----|--------|
| `↑/↓` or `j/k` | Navigate files |
| `Tab` or `h/l` | Switch between left/right columns |
| `Enter` | Toggle file selection in active column |
| `ESC` | Confirm selection and proceed to comparison |
| `q` | Quit application |

### Record List Screen

| Key | Action |
|-----|--------|
| `↑/↓` or `j/k` | Navigate records |
| `g` | Jump to first record |
| `G` | Jump to last record |
| `Enter` | Open comparison view |
| `ESC` / `b` | Back to file list (directory mode) or quit |
| `X` | Export all records (processed) to output directory |

### Comparison Screen

| Key | Action |
|-----|--------|
| `ESC` / `b` | Back to record list |
| `Tab` | Switch panel focus |
| `←` or `h` | Focus left panel |
| `→` or `l` | Focus right panel |
| `j/k` | Navigate tree nodes (same as `↓/↑`) |
| `s` | Toggle sync scroll |
| `d` | Toggle diff highlighting |
| `m` | Show field detail modal |
| `e` | Expand all nodes |
| `c` | Collapse all nodes |
| `x` | Export current record (processed) to output directory |
| `↑/↓` | Navigate tree nodes |
| `Enter` | Expand/collapse node |

### Split Comparison Screen

| Key | Action |
|-----|--------|
| `ESC` | Go back one level in active pane |
| `Tab` | Switch pane focus |
| `h` | Focus left pane |
| `l` | Focus right pane |
| `j/k` | Navigate current widget (files/records/tree) |
| `s` | Toggle sync scroll (when both panes at JSON view) |
| `d` | Toggle diff highlighting (when both panes at JSON view) |
| `q` | Quit application |

### Dataset Comparison Screen

Note: In this screen, `j/k` are used for record navigation instead of cursor navigation.

| Key | Action |
|-----|--------|
| `ESC` / `b` | Back to file selection |
| `Tab` | Switch panel focus |
| `←` or `h` | Focus left panel |
| `→` or `l` | Focus right panel |
| `n/p` | Next/previous record in left panel |
| `N/P` | First/last record in left panel |
| `j/k` | Next/previous record in right panel |
| `J/K` | First/last record in right panel |
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

### Comparison Select Screen (Directory Comparison Mode)

When comparing two directories, a two-column file picker appears:

| Column | Description |
|--------|-------------|
| FILE NAME | Name of the data file |
| FORMAT | File format (JSONL, JSON, PARQUET) |
| SIZE | File size (B, KB, MB, GB) |

**Navigation:**

- Left column: Left dataset files
- Right column: Right dataset files
- `Tab` switches between columns
- `Enter` toggles file selection
- `ESC` confirms selection and proceeds to comparison
- Selected files are highlighted in the secondary color

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

- Use arrow keys or vim keys (`j/k`) to navigate records
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

### Dataset Comparison Screen

When comparing two datasets (using `--compare`), you see a side-by-side comparison of records from both datasets:

- **Left panel**: Dataset A (blue header showing filename)
- **Right panel**: Dataset B (green header showing filename)

Features:

- **No parsing**: Records are displayed as-is from both datasets
- **UUID matching**: Records are matched by UUID if available, with index fallback
- **Synchronized scrolling**: Both panels scroll together (toggle with `s`)
- **Synchronized expansion**: Expanding/collapsing nodes mirrors to other panel
- **Diff highlighting**: Shows differences between the two datasets (toggle with `d`)
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

### Comparing Two Datasets

1. Launch the TUI with the `--compare` flag:
   ```bash
   uv run python -m scripts.tui.app dataset_v1.jsonl --compare dataset_v2.jsonl
   ```

2. Both datasets load side-by-side in the Dataset Comparison Screen

3. Records are matched by UUID (if present) or by index

4. Use `d` to toggle diff highlighting and see differences between datasets

5. Press `ESC` to exit comparison mode

### Comparing Two Directories

1. Launch with two directory paths:
   ```bash
   uv run python -m scripts.tui.app dataset_a/ --compare dataset_b/
   ```

2. A two-column file picker appears

3. Use `↑/↓` to navigate, `Tab` to switch columns

4. Press `Enter` to select a file from each column

5. Press `ESC` to confirm and view the comparison

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
- In comparison mode, both datasets are cached separately

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

**Dataset Comparison Mode:**

When comparing two datasets (not original vs processed), diff highlighting shows:

- **Added content**: Fields/values in right dataset not in left
- **Removed content**: Fields/values in left dataset not in right
- **Changed content**: Same fields with different values
- **Unchanged content**: Identical fields and values

### JSON Tree

Records are displayed as collapsible trees:

- Objects show their keys
- Arrays show their indices
- Primitives show their values
- Nested structures are indented

## Current Limitations

The TUI is currently optimized for AI conversation datasets. Some limitations for general use:

| Area | Current Behavior | Future Plan |
|------|------------------|-------------|
| Schema Detection | Looks for `role/content` messages | Configurable field patterns |
| Record Preview | Shows first "user" message | Configurable preview field |
| Panel Labels | "Original Record" / "Parsed Output" | Parameterized labels |
| Record Matching | Index-based only | ID-based matching with fallback |
| Transformation | Always applies parser_finale | Optional/pluggable transformation |

**Raw Mode Fallback**: If the TUI cannot detect a standard message field, it enters "raw mode" showing the original data on both panels without transformation.

For detailed analysis of generality and the roadmap to support any dataset type, see [Generality Analysis](generality.md).
