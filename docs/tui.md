# TUI Application Guide

The TUI provides an interactive way to browse and compare datasets. Supports JSONL, JSON, and Parquet formats.

## Quick Start

```bash
# Browse a single file (shows original vs. parsed)
uv run python -m scripts.tui.app dataset/conversations.jsonl

# Browse a directory
uv run python -m scripts.tui.app dataset/

# Compare two directories
uv run python -m scripts.tui.app dataset_a/ --compare dataset_b/
```

## Supported Formats

| Format | Extensions | Description |
|--------|------------|-------------|
| JSONL | `.jsonl` | One JSON object per line |
| JSON | `.json` | JSON array of objects |
| Parquet | `.parquet`, `.pq` | Apache Parquet columnar format |

## Options

| Option | Description |
|--------|-------------|
| `-O, --output-dir` | Output directory for export operations (default: `parsed_datasets`) |
| `-c, --compare` | Path to second dataset for side-by-side comparison |

## Single File / Directory Mode

Browse a dataset and view original vs. parsed records:

```bash
uv run python -m scripts.tui.app dataset/conversations.jsonl
uv run python -m scripts.tui.app dataset/
```

**Flow:** File List → Record List → Comparison View

In the comparison view:
- **Left panel**: Original record
- **Right panel**: Parsed output (assistant content emptied, reasoning removed)

This is useful for reviewing what `parser_finale` does to your data.

## Dataset Comparison Mode

Compare two directories side-by-side (no parsing applied):

```bash
uv run python -m scripts.tui.app left_dataset/ --compare right_dataset/
```

This opens a dual-pane view where each side has independent navigation:

1. **File List** → Select a file to open
2. **Record List** → Select a record to view
3. **JSON View** → See the full record as a tree

Use `h/l` or `Tab` to switch between panes. Each pane navigates independently.

### Features

- **JSON tree view**: Expand/collapse nested structures

## Keybindings

### Navigation

| Key | Action |
|-----|--------|
| `j/k` or `↑/↓` | Move up/down |
| `h/l` | Switch pane focus (left/right) |
| `Tab` | Switch pane focus |
| `Enter` | Select item / Expand node |
| `ESC` or `b` | Go back |
| `q` | Quit |

### Export

| Key | Screen | Action |
|-----|--------|--------|
| `P` | File List | Export all files in directory |
| `X` | Record List | Export all records in file |
| `x` | Comparison | Export current record |

Exports go to the directory specified by `-O` (default: `parsed_datasets/`).

## Schema Detection

The TUI automatically detects field mappings:

- **ID fields**: `uuid`, `id`, `uid`, `example_id`, `trial_name`, `chat_id`, `conversation_id`
- **Message fields**: Arrays with `role` or `content` keys
- **Tool fields**: Arrays with `function` or `name` keys

If no standard schema is detected, the TUI shows raw JSON data.

## Tips

- **Large files**: Files over 100MB show a loading progress indicator
- **Caching**: Records are cached after first load for fast navigation
- **Format detection**: Automatic from file extension

## Current Limitations

| Area | Current Behavior | Future Plan |
|------|------------------|-------------|
| Record Matching | Index-based only | ID-based matching |
| Schema Detection | AI conversation patterns | Configurable patterns |
| Panel Labels | Hardcoded | Parameterized |
