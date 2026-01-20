# Plan: Output Directory Support for Parsed Content

## Overview

Add `--output-dir` argument to both `parser_finale.py` CLI and the TUI to save processed/parsed records to a directory (default: `parsed_datasets/`).

---

## Current State

### parser_finale.py CLI
- **Entry point**: `scripts/parser_finale.py`
- **Current output options**:
  - `-o, --output`: Single output file path
  - Defaults to stdout if not specified
- **Behavior**: When given a directory path, launches TUI instead of processing

### TUI
- **Entry points**:
  1. Direct: `python -m scripts.tui.app <path>`
  2. Indirect: When `parser_finale.py` receives a directory
- **Current output**: None - TUI is read-only for viewing only
- **No export/save functionality exists**

---

## Proposed Changes

### 1. Add `--output-dir` Argument to parser_finale.py

**File**: `scripts/parser_finale.py`

**Changes**:
- Add new argument: `--output-dir` / `-O` (capital O to distinguish from `-o`)
  - Default: `parsed_datasets`
  - Type: directory path (created if doesn't exist)
- Modify output logic:
  - When `--output-dir` is specified AND processing a single file:
    - Save to `<output_dir>/<original_filename>_parsed.<format>`
  - When `--output-dir` is specified AND processing multiple files (via directory TUI):
    - Pass output_dir to TUI for batch export
- Ensure mutual exclusivity or precedence between `-o` (single file) and `-O` (directory)

**Location in code**: Lines 252-300 (argparse section)

### 2. Add Export Functionality to TUI

**Files**:
- `scripts/tui/app.py` - Accept output_dir parameter
- `scripts/tui/views/record_list.py` - Add export action
- `scripts/tui/views/comparison_screen.py` - Add export current record action (optional)

**Changes**:

#### a. TUI Constructor (`app.py`)
- Add `output_dir: str | None = None` parameter to `JsonComparisonApp.__init__`
- Store as instance attribute
- Pass to child screens

#### b. CLI Arguments (`app.py:main()`)
- Add `--output-dir` argument to TUI's argparse (line ~355)
- Default: `parsed_datasets`
- Pass to app constructor

#### c. Export Actions (new functionality)
- **Option A**: Auto-export on record navigation (saves each viewed record)
- **Option B**: Manual export via keybinding (e.g., `x` to export current record)
- **Option C**: Batch export all records (e.g., `X` or menu option)

**Recommended**: Option C (batch export) + Option B (single record export)

#### d. Export Logic
Create new function in `data_loader.py` or dedicated `exporter.py`:
```python
def export_records(
    records: list[dict],
    output_dir: str,
    source_filename: str,
    format: str = "json"
) -> None:
    """Export processed records to output directory."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(
        output_dir,
        f"{Path(source_filename).stem}_parsed.{format}"
    )
    # Write records using existing format functions
```

### 3. Update parser_finale.py Directory Mode

**File**: `scripts/parser_finale.py` (lines 310-319)

**Changes**:
- When launching TUI from directory mode, pass `output_dir` if specified:
```python
app = JsonComparisonApp(
    str(path),
    input_format=args.input_format,
    is_directory=True,
    output_dir=args.output_dir  # NEW
)
```

---

## Implementation Tasks

### Phase 1: CLI-only output directory support
1. [ ] Add `--output-dir` argument to `parser_finale.py`
2. [ ] Implement directory output logic for single-file processing
3. [ ] Create output filename from source filename
4. [ ] Ensure output directory is created if missing

### Phase 2: TUI integration
5. [ ] Add `output_dir` parameter to `JsonComparisonApp`
6. [ ] Add `--output-dir` argument to TUI's own CLI
7. [ ] Create export utility function
8. [ ] Add keybinding for single-record export (`x`)
9. [ ] Add keybinding for batch export all records (`X`)
10. [ ] Display export status/confirmation in TUI

### Phase 3: parser_finale + TUI integration
11. [ ] Pass `output_dir` from parser_finale to TUI when launching directory mode
12. [ ] Ensure consistent behavior between both entry points

### Phase 4: Documentation & Polish
13. [ ] Update `docs/cli.md` with new arguments
14. [ ] Update `docs/tui.md` with export keybindings
15. [ ] Add user feedback (success messages, error handling)

---

## File Changes Summary

| File | Changes |
|------|---------|
| `scripts/parser_finale.py` | Add `--output-dir` arg, directory output logic |
| `scripts/tui/app.py` | Add `output_dir` param, CLI arg, pass to screens |
| `scripts/tui/data_loader.py` | Add `export_records()` function |
| `scripts/tui/views/record_list.py` | Add batch export keybinding |
| `scripts/tui/views/comparison_screen.py` | Add single export keybinding |
| `docs/cli.md` | Document new `--output-dir` argument |
| `docs/tui.md` | Document export keybindings |

---

## Default Behavior

- **Default output directory**: `parsed_datasets/`
- **Output filename pattern**: `{original_stem}_parsed.{format}`
- **Example**:
  - Input: `dataset/train.jsonl`
  - Output: `parsed_datasets/train_parsed.json`

---

## Open Questions

1. **Format for TUI exports**: Should TUI inherit format from source file or always use JSON?
2. **Overwrite behavior**: Prompt, overwrite silently, or error on existing files?
3. **Progress indication**: Show progress bar for large batch exports?
