# Code Quality Improvement Plan

## Overview

This plan addresses code duplication across TUI views by extracting shared patterns into reusable mixins and base classes.

## Current State (After Refactoring)

| File | Lines | Purpose |
|------|-------|---------|
| `comparison_screen.py` | ~400 | Original ↔ Parsed JSON comparison |
| `dual_record_list_screen.py` | ~350 | Side-by-side dataset browsing |
| `file_list.py` | 200 | Directory file picker |
| `record_list.py` | 270 | Record table with selection |

**Achieved**: Centralized bindings and panel logic via mixins.

---

## Phase 1: Extract DualPaneMixin ✅ COMPLETED

**Status**: Implemented and working

### What Was Extracted

Created `scripts/tui/mixins/dual_pane.py` with:

```python
class DualPaneMixin:
    """Mixin for screens with left/right panel switching."""

    # Centralized bindings - change here to update ALL dual-pane screens
    PANE_BINDINGS = [
        Binding("tab", "switch_panel", "Switch Panel", show=True),
        Binding("left", "focus_left", "Left Panel", show=False),
        Binding("right", "focus_right", "Right Panel", show=False),
        Binding("escape", "go_back", "Back", show=True),
        Binding("b", "go_back", "Back", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("m", "show_field_detail", "View Field", show=True),
    ]

    _active_panel: str = "left"

    # Panel switching
    def action_switch_panel(self) -> None: ...
    def action_vim_left(self) -> None: ...
    def action_vim_right(self) -> None: ...
    def action_focus_left(self) -> None: ...
    def action_focus_right(self) -> None: ...

    # Common actions
    def action_go_back(self) -> None: ...      # Default: pop_screen
    def action_quit(self) -> None: ...          # Exit app
    def action_show_field_detail(self) -> None: ...  # Show modal

    # Message handlers
    def on_json_tree_panel_node_selected(self, message) -> None: ...

    # Style management
    def _update_panel_styles(self) -> None: ...
    def _focus_active_widget(self) -> None: ...  # Abstract
```

### Usage in Screens

```python
# Both screens now use identical pattern:
class DualRecordListScreen(VimNavigationMixin, DualPaneMixin, Screen):
    BINDINGS = VimNavigationMixin.VIM_BINDINGS + DualPaneMixin.PANE_BINDINGS

class ComparisonScreen(VimNavigationMixin, DualPaneMixin, Screen):
    BINDINGS = (
        VimNavigationMixin.VIM_BINDINGS
        + DualPaneMixin.PANE_BINDINGS
        + [
            # Screen-specific bindings only
            Binding("s", "toggle_sync", "Sync Scroll"),
            Binding("d", "toggle_diff", "Show Diff"),
            # ...
        ]
    )
```

### Impact

- **Lines removed**: ~80 lines from each dual-pane screen
- **Centralized**: 7 keybindings now defined in ONE place
- **Shared methods**: 10+ methods now inherited from mixin
- **Consistency**: Both screens behave identically for common operations

---

## Phase 2: Extract Shared CSS ✅ COMPLETED

**Status**: Implemented

### What Was Done

Created `scripts/tui/styles/base.tcss` with shared styles:
- DataTable styling (header, cursor, hover)
- Panel active/inactive states
- Panel header styling
- Common layout patterns

### Usage

```python
class DualRecordListScreen(VimNavigationMixin, DualPaneMixin, Screen):
    CSS_PATH = "../styles/base.tcss"

class ComparisonScreen(VimNavigationMixin, DualPaneMixin, Screen):
    CSS_PATH = "../styles/base.tcss"
```

### Impact

- **Single source**: All dual-pane styling in one file
- **Consistency**: Identical look and feel across screens
- **Maintenance**: Change once, updates everywhere

---

## Phase 3: Extract DataTableMixin ✓ COMPLETED

**Status**: Implemented

### Implementation

`DataTableMixin` was extracted to `scripts/tui/mixins/data_table.py` with methods:
- `_configure_table()` - Apply configuration to a DataTable
- `_setup_table()` - Set up table with columns and settings
- `_should_skip_table()` - Check if table should be skipped for single records
- `_get_record_id_display()` - Get display string for record ID
- `_get_selected_row_key()` - Extract row key from selection events
- `_get_clicked_row_key()` - Extract row key from click events

`RecordTableMixin` now inherits from `DataTableMixin` for schema-aware record tables.

---

## Phase 4: Extract ExportMixin ⏸️ DEFERRED

**Status**: Future plan (low priority)

### Rationale

Export functionality is screen-specific enough that a mixin would add complexity without significant benefit. May revisit if export features expand.

---

## File Structure (Current)

```
scripts/tui/
├── app.py                    # App entry point
├── mixins/
│   ├── __init__.py          # Exports: VimNavigationMixin, DualPaneMixin
│   ├── vim_navigation.py    # j/k/h/l/g/G navigation
│   ├── dual_pane.py         # ✅ Panel switching, bindings, modal
│   ├── data_table.py        # (exists but minimal use)
│   └── export.py            # (exists but minimal use)
├── styles/
│   └── base.tcss            # ✅ Shared CSS styles
├── views/
│   ├── comparison_screen.py  # ✅ Uses DualPaneMixin
│   ├── dual_record_list_screen.py  # ✅ Uses DualPaneMixin
│   ├── file_list.py
│   └── record_list.py
└── widgets/
    ├── json_tree_panel.py
    ├── diff_indicator.py
    └── field_detail_modal.py
```

---

## Benefits Achieved

### 1. Centralized Keybindings

**Before**: Bindings duplicated in each screen file
```python
# comparison_screen.py
BINDINGS = [...Binding("tab", "switch_panel"...)...]

# dual_record_list_screen.py
BINDINGS = [...Binding("tab", "switch_panel"...)...]  # Duplicate!
```

**After**: Single source of truth
```python
# mixins/dual_pane.py
PANE_BINDINGS = [Binding("tab", "switch_panel"...), ...]

# All screens inherit automatically
BINDINGS = VimNavigationMixin.VIM_BINDINGS + DualPaneMixin.PANE_BINDINGS
```

### 2. Shared Behavior

| Method | Before | After |
|--------|--------|-------|
| `action_switch_panel` | 2 copies | 1 in mixin |
| `action_vim_left/right` | 2 copies | 1 in mixin |
| `action_focus_left/right` | 2 copies | 1 in mixin |
| `action_go_back` | 2 copies | 1 in mixin (overridable) |
| `action_quit` | 2 copies | 1 in mixin |
| `action_show_field_detail` | 1 copy | 1 in mixin (shared!) |
| `_update_panel_styles` | 2 copies | 1 in mixin |

### 3. Easy Customization

To change a keybinding for ALL dual-pane screens:
1. Edit `scripts/tui/mixins/dual_pane.py`
2. Modify `PANE_BINDINGS`
3. Done - all screens update automatically

---

## Testing

All screens verified working:
- Single file mode: `python scripts/tui/app.py data.jsonl`
- Directory mode: `python scripts/tui/app.py dataset/`
- Comparison mode: `python scripts/tui/app.py --compare dir_a dir_b`

---

## Lessons Learned

### 1. Mixin Order Matters

```python
# Correct - Screen must be last for MRO
class MyScreen(VimNavigationMixin, DualPaneMixin, Screen):
```

### 2. Binding Inheritance

```python
# Combine binding lists explicitly
BINDINGS = Mixin1.BINDINGS + Mixin2.BINDINGS + [local bindings]
```

### 3. Abstract Methods

Use `NotImplementedError` for methods subclasses must implement:
```python
def _focus_active_widget(self) -> None:
    raise NotImplementedError(f"{self.__class__.__name__} must implement...")
```

### 4. Local Imports for Circular Dependencies

```python
def action_show_field_detail(self) -> None:
    from scripts.tui.widgets.json_tree_panel import JsonTreePanel  # Local import
```

---

