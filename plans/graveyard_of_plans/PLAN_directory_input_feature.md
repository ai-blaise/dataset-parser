# Implementation Plan: Directory Input Feature for parser_finale TUI

## Overview

Add the ability to pass a directory of input files to `parser_finale` TUI. When a directory is provided, the TUI will display a file selection screen listing all supported files (JSON, JSONL, Parquet) in that directory. Selecting a file will navigate to the existing two-pane comparison view.

## Current Architecture Summary

### Entry Point
- **File:** `scripts/parser_finale.py`
- Uses `argparse` with positional `filename` argument
- Validates file existence with `os.path.exists()`
- Auto-detects format via `scripts.data_formats.detect_format()`

### TUI Structure
- **App:** `scripts/tui/app.py` - `JsonComparisonApp`
- **Screens:**
  - `RecordListScreen` - DataTable of records in a file
  - `ComparisonScreen` - Two-pane JSON comparison view
  - `LoadingScreen` - Progress display for large files

### Parsers
- **Location:** `scripts/data_formats/`
- **Supported:** JSON (`.json`), JSONL (`.jsonl`), Parquet (`.parquet`, `.pq`)
- **Factory:** `get_loader(filename)` auto-detects and returns appropriate loader

### Keybindings (to preserve)
| Screen | Key | Action |
|--------|-----|--------|
| Global | `q` | Quit |
| RecordList | `↑/↓` | Navigate, `Enter` select |
| Comparison | `Escape/b` | Back |
| Comparison | `Tab` | Switch panel |
| Comparison | `Left/Right` | Focus panel |
| Comparison | `s` | Toggle sync |
| Comparison | `d` | Toggle diff |
| Comparison | `m` | View field modal |
| Comparison | `e/c` | Expand/collapse all |

---

## Implementation Plan

### Phase 1: CLI Argument Changes

**File:** `scripts/parser_finale.py`

1. Modify argparse to accept path (file OR directory):
   ```python
   parser.add_argument(
       "path",  # Renamed from "filename"
       help="Path to data file or directory of data files (JSONL, JSON, or Parquet)"
   )
   ```

2. Add path type detection:
   ```python
   import os
   path = args.path
   is_directory = os.path.isdir(path)
   ```

3. Pass `is_directory` flag to TUI app initialization

### Phase 2: Directory File Discovery

**New File:** `scripts/data_formats/directory_loader.py`

Create utility functions for directory scanning:

```python
from pathlib import Path
from scripts.data_formats import EXTENSION_MAP

SUPPORTED_EXTENSIONS = frozenset(EXTENSION_MAP.keys())

def discover_data_files(directory: str) -> list[dict]:
    """
    Discover all supported data files in a directory.

    Returns list of dicts with:
    - path: absolute path to file
    - name: filename
    - format: detected format (jsonl, json, parquet)
    - size: file size in bytes
    """
    dir_path = Path(directory)
    files = []

    for ext in SUPPORTED_EXTENSIONS:
        for file_path in dir_path.glob(f"*{ext}"):
            if file_path.is_file():
                files.append({
                    "path": str(file_path.absolute()),
                    "name": file_path.name,
                    "format": EXTENSION_MAP[ext],
                    "size": file_path.stat().st_size,
                })

    # Sort by name for consistent ordering
    return sorted(files, key=lambda f: f["name"].lower())

def format_file_size(size_bytes: int) -> str:
    """Format file size for display (e.g., '1.2 MB')."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
```

**Update:** `scripts/data_formats/__init__.py`
- Export `discover_data_files` and `format_file_size`

### Phase 3: New File Selection Screen

**New File:** `scripts/tui/views/file_list.py`

Create `FileListScreen` - a new screen for selecting files from a directory:

```python
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header, Footer, Static
from textual.binding import Binding
from textual.message import Message

class FileListScreen(Screen):
    """Screen for selecting a file from a directory."""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "quit", "Quit", show=True),
    ]

    class FileSelected(Message):
        """Posted when a file is selected."""
        def __init__(self, file_path: str, file_name: str) -> None:
            self.file_path = file_path
            self.file_name = file_name
            super().__init__()

    def __init__(self, directory: str, files: list[dict]) -> None:
        super().__init__()
        self._directory = directory
        self._files = files

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Directory: {self._directory}", id="dir-header")
        yield DataTable(id="file-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#file-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Add columns
        table.add_column("FILE NAME", width=50)
        table.add_column("FORMAT", width=10)
        table.add_column("SIZE", width=12)

        # Add rows
        for file_info in self._files:
            table.add_row(
                file_info["name"],
                file_info["format"].upper(),
                format_file_size(file_info["size"]),
                key=file_info["path"],  # Use path as row key
            )

        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle file selection."""
        file_path = str(event.row_key.value)
        file_name = self._files[event.cursor_row]["name"]
        self.post_message(self.FileSelected(file_path, file_name))
```

**CSS additions for `file_list.py`:**
```css
#dir-header {
    background: $primary-background;
    color: $text;
    padding: 1;
    text-align: center;
    text-style: bold;
}

#file-table {
    height: 1fr;
}
```

### Phase 4: App Flow Modifications

**File:** `scripts/tui/app.py`

1. **Add new app modes:**
   ```python
   class AppMode(Enum):
       SINGLE_FILE = "single_file"
       DIRECTORY = "directory"
   ```

2. **Modify `__init__` to accept directory:**
   ```python
   def __init__(
       self,
       path: str,
       input_format: str = "auto",
       is_directory: bool = False,
   ) -> None:
       super().__init__()
       self._path = path
       self._input_format = input_format
       self._is_directory = is_directory
       self._current_file: str | None = None  # Track selected file in dir mode
   ```

3. **Update `on_mount` for directory mode:**
   ```python
   async def on_mount(self) -> None:
       if self._is_directory:
           # Discover files and show file list
           files = discover_data_files(self._path)
           if not files:
               # Show error - no supported files found
               self.exit(message=f"No supported files found in {self._path}")
               return
           self.push_screen(FileListScreen(self._path, files))
       else:
           # Existing single-file logic
           await self._load_single_file(self._path)
   ```

4. **Handle FileSelected message:**
   ```python
   def on_file_list_screen_file_selected(
       self,
       event: FileListScreen.FileSelected
   ) -> None:
       """Handle file selection from directory listing."""
       self._current_file = event.file_path
       # Load the selected file and show record list
       self.run_worker(self._load_single_file(event.file_path))
   ```

5. **Update back navigation from RecordListScreen:**
   - In directory mode: go back to FileListScreen
   - In single file mode: quit app (existing behavior)

### Phase 5: Navigation Flow Updates

**Updated Screen Flow:**

```
Directory Mode:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  FileListScreen │ ──▶ │ RecordListScreen│ ──▶ │ComparisonScreen │
│  (file picker)  │     │   (record list) │     │  (two-pane)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       │                       │
        │                       │ Escape/b              │ Escape/b
        └───────────────────────┘                       │
                                ▲                       │
                                └───────────────────────┘

Single File Mode (unchanged):
┌─────────────────┐     ┌─────────────────┐
│ RecordListScreen│ ──▶ │ComparisonScreen │
│   (record list) │     │  (two-pane)     │
└─────────────────┘     └─────────────────┘
```

**File:** `scripts/tui/views/record_list.py`

Add back navigation support for directory mode:
```python
BINDINGS = [
    Binding("q", "quit", "Quit", show=False),
    Binding("escape", "go_back", "Back", show=True),  # New binding
    Binding("b", "go_back", "Back", show=False),
]

def action_go_back(self) -> None:
    """Go back to file list (directory mode) or quit."""
    self.app.pop_screen()
```

### Phase 6: Update parser_finale.py Main Logic

**File:** `scripts/parser_finale.py`

```python
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse datasets and output content with emptied assistant responses..."
    )
    parser.add_argument(
        "path",
        help="Path to data file or directory of data files (JSONL, JSON, or Parquet)"
    )
    parser.add_argument(
        "--input-format",
        choices=["auto", "jsonl", "json", "parquet"],
        default="auto",
        help="Input file format (default: auto-detect from extension)"
    )
    # ... other args ...

    args = parser.parse_args()

    # Determine if path is file or directory
    if os.path.isdir(args.path):
        # Directory mode - launch TUI with file picker
        from scripts.tui.app import JsonComparisonApp
        app = JsonComparisonApp(
            path=args.path,
            input_format=args.input_format,
            is_directory=True,
        )
        app.run()
    elif os.path.isfile(args.path):
        # Single file mode - existing behavior
        # ... existing processing logic ...
    else:
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/data_formats/directory_loader.py` | Directory scanning utilities |
| `scripts/tui/views/file_list.py` | File selection screen |

## Files to Modify

| File | Changes |
|------|---------|
| `scripts/parser_finale.py` | CLI argument changes, directory detection |
| `scripts/tui/app.py` | Directory mode support, new screen flow |
| `scripts/tui/views/record_list.py` | Back navigation for directory mode |
| `scripts/data_formats/__init__.py` | Export new directory functions |

---

## Keybindings Summary (All Preserved)

### FileListScreen (New)
| Key | Action | Description |
|-----|--------|-------------|
| `↑/↓` | Navigate | Move through file list |
| `Enter` | Select | Open selected file |
| `Escape` | Quit | Exit application |
| `q` | Quit | Exit application |

### RecordListScreen (Updated)
| Key | Action | Description |
|-----|--------|-------------|
| `↑/↓` | Navigate | Move through records |
| `Enter` | Select | View record comparison |
| `Escape/b` | Back | Return to file list (dir mode) or quit |
| `q` | Quit | Exit application |

### ComparisonScreen (Unchanged)
| Key | Action | Description |
|-----|--------|-------------|
| `Escape/b` | Back | Return to record list |
| `Tab` | Switch | Toggle panel focus |
| `Left/Right` | Focus | Direct panel focus |
| `s` | Sync | Toggle scroll sync |
| `d` | Diff | Toggle diff highlight |
| `m` | Modal | View field detail |
| `e` | Expand | Expand all nodes |
| `c` | Collapse | Collapse all nodes |
| `q` | Quit | Exit application |

---

## Testing Checklist

- [ ] Directory with mixed formats (JSON, JSONL, Parquet) shows all files
- [ ] Empty directory shows appropriate error message
- [ ] Directory with no supported files shows error
- [ ] File selection navigates to record list correctly
- [ ] Back from record list returns to file list (directory mode)
- [ ] Back from record list quits (single file mode)
- [ ] All existing keybindings work unchanged
- [ ] Single file mode works exactly as before
- [ ] Large directories load efficiently
- [ ] File sizes display correctly

---

## Future Enhancements (Out of Scope)

- Recursive directory scanning with `--recursive` flag
- File filtering by format in the file list
- Search/filter within file list
- Recently opened files
- File metadata preview (record count, etc.)
