# Split-Screen Dataset Comparison Feature

## Overview

A comparison mode for the TUI enabling side-by-side comparison of two arbitrary datasets. Two modes:

1. **Dual Record List** (`--compare`): Each pane navigates independently through: FILE_LIST → RECORD_LIST → JSON_VIEW
2. **Comparison Screen** (single file): Shows original ↔ processed with diff highlighting and sync scrolling

## Usage

```bash
# Compare two directories (full navigation: file → records → JSON)
PYTHONPATH=. uv run python scripts/tui/app.py --compare test_comparison/dataset_a test_comparison/dataset_b

# Short flag version
PYTHONPATH=. uv run python scripts/tui/app.py -c dataset_a/ dataset_b/

# Single file comparison (original vs processed with diffs)
PYTHONPATH=. uv run python scripts/tui/app.py test_comparison/dataset_a/conversations.jsonl
```

## Key UX Principles

1. **Independent panes (Dual Record List)**: Each pane navigates its own flow completely independently
2. **No reliance between panes**: Left can be at JSON_VIEW while right is still at FILE_LIST
3. **Enter drills down**: Select file → load records, select record → show JSON
4. **Escape goes back**: JSON_VIEW → RECORD_LIST → FILE_LIST → Exit
5. **Tab switches focus**: Move between left and right panes
6. **'d' toggles diffs** (ComparisonScreen only): Highlight differences between original/processed
7. **'s' toggles sync scroll** (ComparisonScreen only): Scroll both panels together

## Keybindings

### Global Pane Bindings (DualPaneMixin)

All pane-related keybindings are centralized in `DualPaneMixin.PANE_BINDINGS`. Change them once to update all dual-pane screens.

| Key | Action | Description |
|-----|--------|-------------|
| `tab` | switch_panel | Switch between left/right panels |
| `left` | focus_left | Focus left panel (arrow key) |
| `right` | focus_right | Focus right panel (arrow key) |
| `h` | vim_left | Focus left panel (vim) |
| `l` | vim_right | Focus right panel (vim) |
| `j/k` | vim_down/up | Navigate within panel |
| `escape` | go_back | Go back one step |
| `b` | go_back | Go back (vim style) |
| `q` | quit | Exit application |
| `m` | show_field_detail | View field in modal (JSON view) |
| `Enter` | (native) | Select item / drill down |

### ComparisonScreen-Specific Bindings

These bindings are only available in the ComparisonScreen (original ↔ processed view).

| Key | Action | Description |
|-----|--------|-------------|
| `s` | toggle_sync | Toggle synchronized scrolling |
| `d` | toggle_diff | Toggle diff highlighting |
| `e` | expand_all | Expand all JSON tree nodes |
| `c` | collapse_all | Collapse all JSON tree nodes |
| `x` | export_record | Export current record |

## Navigation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│               Dataset Comparison - Independent Panes             │
├───────────────────────────┬─────────────────────────────────────┤
│      LEFT PANE (active)   │           RIGHT PANE                │
│                           │                                     │
│  State: FILE_LIST         │   State: FILE_LIST                  │
│  ┌─────────────────────┐  │   ┌─────────────────────────────┐   │
│  │ > file1.jsonl       │  │   │ > file1.jsonl               │   │
│  │   file2.jsonl       │  │   │   file2.parquet             │   │
│  │   samples.json      │  │   │   data.json                 │   │
│  └─────────────────────┘  │   └─────────────────────────────┘   │
│                           │                                     │
├───────────────────────────┴─────────────────────────────────────┤
│ [Tab] Switch Panel  [Esc] Back  [m] View Field  [Enter] Select  │
└─────────────────────────────────────────────────────────────────┘
```

### Pane States

| State | Shows | Enter Action | Escape Action |
|-------|-------|--------------|---------------|
| `FILE_LIST` | File picker table | Select file → `RECORD_LIST` | Exit comparison mode |
| `RECORD_LIST` | Record table | Select record → `JSON_VIEW` | Go back → `FILE_LIST` |
| `JSON_VIEW` | JSON tree | Expand/collapse node | Go back → `RECORD_LIST` |

## Architecture

### Mixin-Based Design

The implementation uses mixins for code reuse across screens:

```python
class DualRecordListScreen(VimNavigationMixin, DualPaneMixin, Screen):
    """Two independent panes, each with FILE_LIST → RECORD_LIST → JSON_VIEW flow."""

    # Inherit ALL common bindings from mixins
    BINDINGS = VimNavigationMixin.VIM_BINDINGS + DualPaneMixin.PANE_BINDINGS
```

### Centralized Bindings

**Location**: `scripts/tui/mixins/dual_pane.py`

```python
class DualPaneMixin:
    # Change these here to update ALL dual-pane screens at once
    PANE_BINDINGS = [
        Binding("tab", "switch_panel", "Switch Panel", show=True),
        Binding("left", "focus_left", "Left Panel", show=False),
        Binding("right", "focus_right", "Right Panel", show=False),
        Binding("escape", "go_back", "Back", show=True),
        Binding("b", "go_back", "Back", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("m", "show_field_detail", "View Field", show=True),
    ]
```

### Shared Functionality in DualPaneMixin

| Method | Purpose |
|--------|---------|
| `action_switch_panel()` | Toggle between left/right panels |
| `action_vim_left()` | Switch to left panel (h key) |
| `action_vim_right()` | Switch to right panel (l key) |
| `action_focus_left()` | Switch to left panel (arrow key) |
| `action_focus_right()` | Switch to right panel (arrow key) |
| `action_go_back()` | Go back (default: pop screen) |
| `action_quit()` | Exit application |
| `action_show_field_detail()` | Show field detail modal |
| `_update_panel_styles()` | Update active/inactive CSS classes |
| `_focus_active_widget()` | Abstract - subclasses implement |

### Critical Pattern: Enter Key Handling

**DO NOT** add explicit `Binding("enter", ...)` - this intercepts DataTable's native handling.

**CORRECT**: Use `on_data_table_row_selected()` message handler:

```python
def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
    """Handle Enter on any DataTable - fires automatically."""
    table_id = event.data_table.id

    if table_id == "left-file-table":
        self._handle_file_selected("left", event)
    elif table_id == "right-file-table":
        self._handle_file_selected("right", event)
    # ... etc
```

## Files

| File | Purpose |
|------|---------|
| `scripts/tui/mixins/dual_pane.py` | **Centralized bindings & panel logic** |
| `scripts/tui/mixins/vim_navigation.py` | Vim j/k/h/l/g/G navigation |
| `scripts/tui/views/dual_record_list_screen.py` | Main comparison screen (independent pane navigation) |
| `scripts/tui/views/comparison_screen.py` | Original ↔ Parsed screen (diff highlighting, sync scroll) |
| `scripts/tui/styles/base.tcss` | Shared CSS styles |
| `scripts/tui/app.py` | App entry point |
| `scripts/tui/widgets/diff_indicator.py` | Diff calculation logic |

## Customizing Keybindings

To change a keybinding for all dual-pane screens:

1. Edit `scripts/tui/mixins/dual_pane.py`
2. Modify the `PANE_BINDINGS` list
3. All screens using `DualPaneMixin` will automatically update

Example - change Tab to Ctrl+Tab:
```python
PANE_BINDINGS = [
    Binding("ctrl+tab", "switch_panel", "Switch Panel", show=True),
    # ... rest unchanged
]
```

## Scope

### What IS Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| Independent pane navigation | ✓ | Each pane navigates independently |
| FILE_LIST → RECORD_LIST → JSON_VIEW flow | ✓ | Per pane |
| Tab switching | ✓ | Move between left/right panels |
| Vim navigation (j/k/h/l) | ✓ | Within active panel |
| Diff highlighting | ✓ | Press `d` to toggle |
| Sync scrolling | ✓ | Press `s` to toggle |
| Field detail modal | ✓ | Press `m` to view field details |
| Raw mode for unknown schemas | ✓ | Shows original on both sides |

### Future Plans

| Feature | Priority | Notes |
|---------|----------|-------|
| Synced record selection | Medium | Currently records selected independently |
| Diff summary | Low | Would show diff counts/statistics |
| Cross-pane search | Medium | Unified search across both panes |
| Export comparison | Low | Export side-by-side comparison results |
| ID-based record matching | High | Match by UUID instead of index |
| Configurable panel labels | Medium | Remove hardcoded "Original"/"Parsed" |

## Test Data Files

### Directory Structure
```
test_comparison/
├── dataset_a/
│   ├── conversations.jsonl    (standard schema: uuid, messages, tools)
│   ├── results_eval.jsonl    (custom schema: example_id, prompt)
│   ├── samples.json
│   └── train_v1.jsonl
└── dataset_b/
    ├── conversations.jsonl    (standard schema with different content)
    ├── results_eval.jsonl    (custom schema - overlapping + new records)
    ├── samples.json
    └── train_v2.jsonl
```

### Schema Formats

**Standard Schema** (`conversations.jsonl`):
```json
{"uuid": "conv-001", "messages": [{"role": "user", "content": "..."}], "tools": [...]}
```

**Custom Schema** (`results_eval.jsonl`):
```json
{"example_id": 0, "prompt": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]}
```

### Testing Scenarios

| Scenario | Left Dataset | Right Dataset | Expected Behavior |
|----------|--------------|---------------|-------------------|
| Same format comparison | dataset_a/conversations.jsonl | dataset_b/conversations.jsonl | Side-by-side record comparison |
| Custom schema comparison | dataset_a/results_eval.jsonl | dataset_b/results_eval.jsonl | Tests dynamic schema detection |
| Mixed schemas | dataset_a/conversations.jsonl | dataset_a/results_eval.jsonl | Each pane detects its own schema |
| Multi-record files | Any file with 5+ records | Any file with 5+ records | Record list table navigation |
| Single-record files | File with 1 record | File with 1 record | Skips record list, goes direct to JSON |

### Verification Commands
```bash
# Compare standard schema files
PYTHONPATH=. uv run python scripts/tui/app.py -c test_comparison/dataset_a/conversations.jsonl test_comparison/dataset_b/conversations.jsonl

# Compare custom schema files (tests dynamic detection)
PYTHONPATH=. uv run python scripts/tui/app.py -c test_comparison/dataset_a/results_eval.jsonl test_comparison/dataset_b/results_eval.jsonl

# Compare entire directories
PYTHONPATH=. uv run python scripts/tui/app.py --compare test_comparison/dataset_a test_comparison/dataset_b
```
