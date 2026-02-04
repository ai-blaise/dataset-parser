# Plan: Dynamic Schema Detection for TUI Record Rendering

## Problem

The TUI record list and comparison screen have **hardcoded field assumptions**:

| Code Location | Hardcoded Fields |
|--------------|-----------------|
| `data_loader.py:299-300` | `messages`, `uuid`, `tools` |
| `data_loader.py:305` | `role == "user"` |
| `data_loader.py:306` | `content` field in messages |

When a JSON file has custom field names (e.g., `chat_history` instead of `messages`), the TUI:
- Shows empty/wrong data in the record list
- Fails to display record previews
- Breaks the comparison screen

## Solution: Dynamic Field Detection with Inheritance

Auto-detect field roles based on structure, then render whatever fields exist using a clean inheritance hierarchy:
- **DataTableMixin** - Base class for generic table operations
- **RecordTableMixin** - Inherits from DataTableMixin, adds record-specific dynamic columns

## Detection Heuristics

| Semantic Role | Detection Rule |
|---------------|----------------|
| **messages** | Array field containing objects with `role` and/or `content` keys. If multiple candidates, prefer largest array. |
| **uuid/id** | Field detection in priority order: (1) field name matches ID patterns (`uuid`, `id`, `uid`, `example_id`, `trial_name`, `chat_id`) with string or integer value, (2) field value matches UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`). |
| **tools** | Array field containing objects with `function` or `name` keys. If multiple candidates, prefer largest array. |
| **preview** | First user message content from detected messages array. Handles `content` as string or array (OpenAI vision format). |

### Handling Edge Cases

- **Multiple candidate fields**: When multiple arrays qualify as messages/tools, select the largest array by length.
- **Nested content arrays**: Some formats (OpenAI vision) have `content` as an array of objects. Extract text from `{type: "text", text: "..."}` items.
- **Mixed schemas in same file**: Detection runs once per file on the first record; assumes consistent schema across records.
- **Integer IDs**: Fields like `example_id: 0` are detected as ID fields (not just string UUIDs).
- **Single record files**: Skip record list and go directly to detail/comparison view.

## Architecture

```
scripts/tui/
├── data_loader.py              # Dynamic detection functions + schema cache
├── mixins/
│   ├── data_table.py          # DataTableMixin (BASE - generic table ops)
│   └── record_table.py        # RecordTableMixin (inherits DataTableMixin)
└── views/
    ├── record_list.py          # Uses RecordTableMixin for dynamic columns
    ├── dual_record_list_screen.py  # Uses RecordTableMixin for comparison mode
    └── comparison_screen.py    # Raw mode for non-standard schemas
```

## Inheritance Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DataTableMixin                                   │
│  (Base class for ALL table views - file lists, record lists, etc.)         │
├─────────────────────────────────────────────────────────────────────────────┤
│  EVENT HANDLING                                                             │
│  ├── _get_selected_row_key(event) → str | None                              │
│  └── _get_clicked_row_key(event) → str | None                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  TABLE CONFIGURATION                                                        │
│  ├── _configure_table(table, columns, cursor_type, zebra_stripes)            │
│  └── _setup_table(table_id, columns) → DataTable                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  GENERIC TABLE POPULATION                                                   │
│  ├── _should_skip_table(records) → bool                                     │
│  └── _get_record_id_display(record) → str                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ inherits
                                    ┌─────────────────────────────────────────┐
                                    │           RecordTableMixin                │
                                    │  (Record-specific: dynamic columns)       │
                                    ├─────────────────────────────────────────┤
                                    │  COLUMN GENERATION                                                │
                                    │  ├── _get_record_columns(mapping) → list[tuple]                   │
                                    │  └── _build_record_row(summary, mapping) → list[str]              │
                                    ├─────────────────────────────────────────┤
                                    │  RECORD POPULATION                                             │
                                    │  └── _populate_record_table(table, records, mapping)             │
                                    │      └── Uses inherited _configure_table()                      │
                                    └─────────────────────────────────────────┘
```

## DataTableMixin (Base Class)

```python
from textual.widgets import DataTable
from textual.events import Click

class DataTableMixin:
    """Mixin providing generic DataTable operations for all views."""

    # === Event Handling ===

    def _get_selected_row_key(self, event: DataTable.RowSelected) -> str | None:
        """Extract row key from RowSelected event."""
        row_key = event.row_key
        if row_key is None:
            return None
        return str(row_key.value)

    def _get_clicked_row_key(self, event: Click) -> str | None:
        """Extract row key from Click event on DataTable."""
        if event.row is None:
            return None
        return str(event.row)

    # === Table Configuration ===

    def _configure_table(
        self,
        table: DataTable,
        columns: list[tuple[str, int | None]],
        *,
        cursor_type: str = "row",
        zebra_stripes: bool = True,
    ) -> None:
        """Configure a DataTable with columns and common settings.

        Args:
            table: The DataTable widget to configure.
            columns: List of (column_name, width) tuples. Width of None means flexible.
            cursor_type: Cursor type ('row', 'cell', or 'none').
            zebra_stripes: Whether to enable zebra striping.
        """
        table.cursor_type = cursor_type
        table.zebra_stripes = zebra_stripes
        for name, width in columns:
            table.add_column(name, width=width)

    def _setup_table(
        self,
        table_id: str,
        columns: list[tuple[str, int]],
        *,
        cursor_type: str = "row",
        zebra_stripes: bool = True,
    ) -> DataTable:
        """Set up a DataTable by ID with columns and common settings.

        Args:
            table_id: The ID of the DataTable widget to configure.
            columns: List of (column_name, width) tuples.
            cursor_type: Cursor type ('row', 'cell', or 'none').
            zebra_stripes: Whether to enable zebra striping.

        Returns:
            The configured DataTable instance.
        """
        table = self.query_one(f"#{table_id}", DataTable)
        self._configure_table(table, columns, cursor_type=cursor_type, zebra_stripes=zebra_stripes)
        return table

    # === Generic Utilities ===

    def _should_skip_table(self, records: list) -> bool:
        """Check if table should be skipped (single item goes to detail view).

        When there's only one record, it's more useful to go directly
        to the detail/comparison view rather than showing a list with
        a single item.

        Args:
            records: List of items to display.

        Returns:
            True if there's exactly one item and table should be skipped.
        """
        return len(records) == 1

    def _get_record_id_display(self, record: dict[str, Any]) -> str:
        """Extract short ID (max 8 chars) from record for display.

        Tries common ID fields in priority order and returns a truncated
        string suitable for display in headers/labels.

        Args:
            record: The record to extract ID from.

        Returns:
            A short string identifier (max 8 chars).
        """
        for field in ["uuid", "id", "example_id", "chat_id", "trial_name", "conversation_id"]:
            if field in record:
                val = record[field]
                val_str = str(val) if val is not None else ""
                return val_str[:8] if len(val_str) > 8 else val_str
        return "Unknown"
```

## RecordTableMixin (Inherits DataTableMixin)

```python
from typing import Any, TYPE_CHECKING
from textual.widgets import DataTable

if TYPE_CHECKING:
    from scripts.tui.data_loader import FieldMapping

class RecordTableMixin(DataTableMixin):
    """Mixin providing dynamic schema-aware record table functionality."""

    # === Dynamic Column Generation ===

    def _get_record_columns(self, mapping: "FieldMapping") -> list[tuple[str, int | None]]:
        """Generate column config based on detected FieldMapping.

        Columns are dynamically included based on what fields are detected:
        - IDX: Always present (row number)
        - ID: Present if uuid/id field detected
        - MSGS: Present if messages field detected
        - TOOLS: Present if tools field detected
        - PREVIEW: Always present (first user message, flexible width)

        Args:
            mapping: The detected field mapping for the dataset.

        Returns:
            List of (column_name, width) tuples.
        """
        cols = [("IDX", 6)]

        if mapping.uuid:
            cols.append(("ID", 15))
        if mapping.messages:
            cols.append(("MSGS", 6))
        if mapping.tools:
            cols.append(("TOOLS", 6))

        cols.append(("PREVIEW", None))  # flexible width
        return cols

    def _build_record_row(self, summary: dict[str, Any], mapping: "FieldMapping") -> list[str]:
        """Build a table row dynamically based on FieldMapping.

        Only includes values for columns that exist in the mapping.
        This ensures rows match the dynamically generated columns.

        Args:
            summary: Record summary from get_record_summary().
            mapping: The detected field mapping for the dataset.

        Returns:
            List of string values for the row.
        """
        row: list[str] = [str(summary["index"])]

        if mapping.uuid:
            row.append(summary["uuid"])
        if mapping.messages:
            row.append(str(summary["msg_count"]))
        if mapping.tools:
            row.append(str(summary["tool_count"]))

        row.append(summary["preview"])
        return row

    # === Record Population ===

    def _populate_record_table(
        self,
        table: DataTable,
        records: list[dict[str, Any]],
        mapping: "FieldMapping",
        get_summary_fn: Any = None,
    ) -> None:
        """Populate a DataTable with records using dynamic columns.

        Clears existing content and adds columns/rows based on the
        detected field mapping. Uses inherited _configure_table() for
        consistent table setup.

        Args:
            table: The DataTable widget to populate.
            records: List of records to display.
            mapping: The detected field mapping for the dataset.
            get_summary_fn: Optional custom summary function. If None,
                           uses get_record_summary from data_loader.
        """
        from scripts.tui.data_loader import get_record_summary

        if get_summary_fn is None:
            get_summary_fn = get_record_summary

        # Get dynamic columns from FieldMapping
        columns = self._get_record_columns(mapping)

        # Configure table (uses inherited _configure_table from DataTableMixin)
        self._configure_table(table, columns)

        # Clear and add rows
        table.clear()
        for idx, record in enumerate(records):
            summary = get_summary_fn(record, idx, mapping)
            row = self._build_record_row(summary, mapping)
            table.add_row(*row, key=str(idx))

    # Override _should_skip_table for clarity (uses base implementation)
    def _should_skip_table(self, records: list[dict[str, Any]]) -> bool:
        """Check if record list should be skipped (single record).

        When there's only one record, skip the record list and go directly
        to the JSON/detail view.

        Args:
            records: List of loaded records.

        Returns:
            True if there's exactly one record and list should be skipped.
        """
        return len(records) == 1
```

## Dataflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FILE LOAD                                        │
└────────────────────────────┬──────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  detect_schema(record) → FieldMapping                        │
│  ┌─────────────┬───────────┬─────────────┬──────────────────┐                │
│  │ uuid_field  │ msgs_field│ tools_field │ preview_strategy │                │
│  │    "x"      │  "chat"   │    None     │ first user msg   │                │
│  └─────────────┴───────────┴─────────────┴──────────────────┘                │
└────────────────────────────┬──────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              _get_record_columns(mapping) → columns                          │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │ INPUT: FieldMapping(uuid="x", messages="chat", tools=None)        │      │
│  │ OUTPUT: [("IDX", 6), ("ID", 15), ("MSGS", 6), ("PREVIEW", None)] │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  DYNAMIC COLUMN ADJUSTMENT:                                                 │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │ FieldMapping(uuid=None, messages=None, tools=None)               │      │
│  │ → [("IDX", 6), ("PREVIEW", None)]  (only IDX + PREVIEW)          │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │ FieldMapping(uuid="id", messages="msgs", tools="fn")              │      │
│  │ → [("IDX", 6), ("ID", 15), ("MSGS", 6), ("TOOLS", 6), ("PREVIEW")]│      │
│  └───────────────────────────────────────────────────────────────────┘      │
└────────────────────────────┬──────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              _configure_table(table, columns)                                │
│  - Sets cursor_type = "row"                                                  │
│  - Sets zebra_stripes = True                                                 │
│  - Adds columns to DataTable                                                 │
└────────────────────────────┬──────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              _populate_record_table()                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ for each record:                                                     │    │
│  │   summary = get_record_summary(record, idx, mapping)               │    │
│  │   row = _build_record_row(summary, mapping)                        │    │
│  │   table.add_row(*row, key=str(idx))                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────┬──────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              _should_skip_table(records)                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ if len(records) == 1:                                               │    │
│  │     PUSH ComparisonScreen/JSON_VIEW (skip record list)             │    │
│  │ else:                                                                │    │
│  │     SHOW DataTable with records                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Views After Refactoring

### FileListScreen (Uses DataTableMixin Only)

```python
class FileListScreen(ExportMixin, DataTableMixin, VimNavigationMixin, Screen):
    """Screen for selecting a file from a directory."""

    def on_mount(self) -> None:
        # Static columns - no dynamic mapping needed
        table = self._setup_table(
            "file-table",
            [
                ("FILE NAME", 50),
                ("FORMAT", 10),
                ("SIZE", 12),
            ],
        )

        # Manual population (no RecordTableMixin needed)
        for file_info in self._files:
            table.add_row(
                file_info["name"],
                file_info["format"].upper(),
                format_file_size(file_info["size"]),
                key=file_info["path"],
            )
```

### RecordListScreen (Uses Both Mixins)

```python
class RecordListScreen(ExportMixin, DataTableMixin, RecordTableMixin, VimNavigationMixin, Screen):
    """Screen that displays a list of JSONL records in a DataTable."""

    def _load_data(self) -> None:
        # Get cached schema mapping
        mapping = get_field_mapping(self.filename) if self.filename else FieldMapping()

        # Dynamic columns based on detected schema
        columns = self._get_record_columns(mapping)
        table = self._setup_table("record-table", columns)

        # Single-record skip (uses inherited _should_skip_table)
        if self._should_skip_table(self._records):
            self._show_record_detail(self._records[0])
            return

        # Populate with dynamic columns
        self._populate_record_table(table, self._records, mapping)
```

### DualRecordListScreen (Uses RecordTableMixin)

```python
class DualRecordListScreen(BackgroundTaskMixin, DualPaneMixin, RecordTableMixin, VimNavigationMixin, Screen):
    """Two independent panes, each with FILE_LIST → RECORD_LIST → JSON_VIEW flow."""

    def _complete_file_load(self, side: str, records: list) -> None:
        # Single-record skip (uses inherited _should_skip_table)
        if self._should_skip_table(records):
            # Single record - go directly to JSON view
            record = records[0]
            self._set_pane_json_view(side, record, 0)
        else:
            # Multiple records - show record list
            self._populate_pane_records(side)

    def _populate_pane_records(self, side: str) -> None:
        """Populate record table for a pane using RecordTableMixin."""
        table = self.query_one(f"#{side}-record-table", DataTable)
        records = self._get_pane_records(side)
        selected_file = self._get_pane_selected_file(side)

        mapping = get_field_mapping(selected_file) if selected_file else FieldMapping()
        self._populate_record_table(table, records, mapping)
```

## Schema Caching Strategy

Detect schema **once per file load**, not per record. Store mapping at module level:

```python
# Global cache for detected schemas
_schema_cache: dict[str, FieldMapping] = {}

def get_field_mapping(filename: str) -> FieldMapping:
    return _schema_cache.get(filename, DEFAULT_MAPPING)

def set_schema_cache(filename: str, mapping: FieldMapping) -> None:
    _schema_cache[filename] = mapping
```

Schema detection happens in `load_all_records()` on the first record.

## Implementation Steps

### Step 1: Add field detection functions (`data_loader.py`)

```python
import re

UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
ID_FIELD_NAMES = {'uuid', 'id', 'uid', 'example_id', 'trial_name', 'chat_id', 'conversation_id'}

def detect_messages_field(record: dict) -> str | None:
    """Find array field with message-like objects (role/content). Prefers largest."""
    candidates = []
    for key, val in record.items():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            if 'role' in val[0] or 'content' in val[0]:
                candidates.append((key, len(val)))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1])[0]  # Return largest

def detect_uuid_field(record: dict) -> str | None:
    """Find field that looks like an ID. Name match takes priority."""
    # Priority 1: Field name matches known ID patterns (string or int value)
    for key, val in record.items():
        if isinstance(val, (str, int)) and key.lower() in ID_FIELD_NAMES:
            return key
    # Priority 2: Value matches UUID format (string only)
    for key, val in record.items():
        if isinstance(val, str) and UUID_PATTERN.match(val):
            return key
    return None

def detect_tools_field(record: dict) -> str | None:
    """Find array field with tool-like objects (function/name). Prefers largest."""
    candidates = []
    for key, val in record.items():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            if 'function' in val[0] or 'name' in val[0]:
                candidates.append((key, len(val)))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1])[0]

def extract_preview(messages: list) -> str:
    """Extract first user message content. Handles string or array content."""
    for msg in messages:
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            # Handle OpenAI vision format: content as array
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        return item.get('text', '')
                return ''
            return content
    return ''
```

### Step 2: Add schema detection function (`data_loader.py`)

```python
@dataclass
class FieldMapping:
    messages: str | None = None
    uuid: str | None = None
    tools: str | None = None

DEFAULT_MAPPING = FieldMapping(messages="messages", uuid="uuid", tools="tools")

def detect_schema(record: dict) -> FieldMapping:
    """Detect field mapping from a sample record. Called once per file."""
    return FieldMapping(
        messages=detect_messages_field(record),
        uuid=detect_uuid_field(record),
        tools=detect_tools_field(record),
    )
```

### Step 3: Update `get_record_summary()` (`data_loader.py`)

```python
def get_record_summary(record: dict, idx: int, mapping: FieldMapping = None) -> dict:
    """Generate summary using pre-detected field mapping."""
    if mapping is None:
        mapping = DEFAULT_MAPPING

    # Extract data using cached mapping
    messages = record.get(mapping.messages, []) if mapping.messages else []
    tools = record.get(mapping.tools, []) if mapping.tools else []
    id_value = record.get(mapping.uuid, "") if mapping.uuid else ""

    # Generate preview from detected messages
    preview_text = extract_preview(messages) if messages else ""
    preview = truncate(preview_text.strip(), 40) if preview_text else ""

    # Convert ID to string (handles both string and integer IDs)
    id_str = str(id_value) if id_value != "" else ""
    id_truncated = truncate(id_str, 8)

    return {
        "index": idx,
        "uuid": id_truncated,
        "msg_count": len(messages),
        "tool_count": len(tools),
        "license": record.get("license", ""),
        "used_in": record.get("used_in", []),
        "reasoning": record.get("reasoning"),
        "preview": preview,
    }
```

### Step 4: Refactor DataTableMixin (`mixins/data_table.py`)

Add `_configure_table()` method and refactor `_setup_table()` to use it:

```python
class DataTableMixin:
    # ... existing _get_selected_row_key, _get_clicked_row_key ...

    def _configure_table(
        self,
        table: DataTable,
        columns: list[tuple[str, int | None]],
        *,
        cursor_type: str = "row",
        zebra_stripes: bool = True,
    ) -> None:
        table.cursor_type = cursor_type
        table.zebra_stripes = zebra_stripes
        for name, width in columns:
            table.add_column(name, width=width)

    def _setup_table(self, table_id: str, columns: list[tuple[str, int]], *, cursor_type: str = "row", zebra_stripes: bool = True) -> DataTable:
        table = self.query_one(f"#{table_id}", DataTable)
        self._configure_table(table, columns, cursor_type=cursor_type, zebra_stripes=zebra_stripes)
        return table

    def _should_skip_table(self, records: list) -> bool:
        return len(records) == 1

    def _get_record_id_display(self, record: dict[str, Any]) -> str:
        for field in ["uuid", "id", "example_id", "chat_id", "trial_name"]:
            if field in record:
                val = record[field]
                val_str = str(val) if val is not None else ""
                return val_str[:8] if len(val_str) > 8 else val_str
        return "Unknown"
```

### Step 5: Refactor RecordTableMixin (`mixins/record_table.py`)

Make it inherit from DataTableMixin and refactor `_populate_record_table()`:

```python
class RecordTableMixin(DataTableMixin):
    """Mixin providing dynamic schema-aware record table functionality."""

    def _get_record_columns(self, mapping: FieldMapping) -> list[tuple[str, int | None]]:
        cols = [("IDX", 6)]
        if mapping.uuid:
            cols.append(("ID", 15))
        if mapping.messages:
            cols.append(("MSGS", 6))
        if mapping.tools:
            cols.append(("TOOLS", 6))
        cols.append(("PREVIEW", None))
        return cols

    def _build_record_row(self, summary: dict[str, Any], mapping: FieldMapping) -> list[str]:
        row = [str(summary["index"])]
        if mapping.uuid:
            row.append(summary["uuid"])
        if mapping.messages:
            row.append(str(summary["msg_count"]))
        if mapping.tools:
            row.append(str(summary["tool_count"]))
        row.append(summary["preview"])
        return row

    def _populate_record_table(
        self,
        table: DataTable,
        records: list[dict[str, Any]],
        mapping: FieldMapping,
        get_summary_fn: Any = None,
    ) -> None:
        from scripts.tui.data_loader import get_record_summary

        if get_summary_fn is None:
            get_summary_fn = get_record_summary

        columns = self._get_record_columns(mapping)
        self._configure_table(table, columns)

        table.clear()
        for idx, record in enumerate(records):
            summary = get_summary_fn(record, idx, mapping)
            row = self._build_record_row(summary, mapping)
            table.add_row(*row, key=str(idx))

    def _should_skip_table(self, records: list[dict[str, Any]]) -> bool:
        return len(records) == 1
```

### Step 6: Update views (minimal changes needed)

- `FileListScreen`: No changes required
- `RecordListScreen`: No changes required (already uses both mixins)
- `DualRecordListScreen`: Replace inline `_should_skip_record_list()` calls with inherited `_should_skip_table()`

### Step 7: Single-record skip in app.py

```python
def _push_appropriate_screen(self) -> None:
    """Push RecordListScreen or ComparisonScreen based on record count."""
    if len(self.records) == 1:
        # Single record - go straight to comparison view
        self.push_screen(ComparisonScreen(self.filename, 0))
    else:
        # Multiple records - show record list for selection
        self.push_screen(RecordListScreen())
```

### Step 8: Raw mode for comparison screen (`comparison_screen.py`)

If no standard fields detected, show original on both panels (skip processing):

```python
def _load_comparison_data(self) -> None:
    self._original, self._processed = load_record_pair(...)

    # Check if schema is non-standard
    has_messages = detect_messages_field(self._original)
    if not has_messages:
        # Show raw data on both sides, no processing
        self._processed = self._original.copy()
        self.notify("Non-standard schema - showing raw data", severity="warning")
```

## Key Files Modified

| File | Action |
|------|--------|
| `scripts/tui/data_loader.py` | Add `detect_*()` functions, `FieldMapping`, schema cache |
| `scripts/tui/mixins/data_table.py` | Add `_configure_table()`, `_should_skip_table()`, `_get_record_id_display()` |
| `scripts/tui/mixins/record_table.py` | Refactor to inherit from DataTableMixin |
| `scripts/tui/mixins/__init__.py` | Ensure both mixins exported |
| `scripts/tui/views/record_list.py` | Use inherited `_should_skip_table()` |
| `scripts/tui/views/dual_record_list_screen.py` | Use inherited methods |
| `scripts/tui/views/file_list.py` | No changes |
| `scripts/tui/app.py` | Single-record skip logic |
| `tests/test_dynamic_schema.py` | CREATE - comprehensive tests |

## Behavior Examples

### Standard Schema (works as before)

```json
{"uuid": "abc123", "messages": [{"role": "user", "content": "Hello"}], "tools": [...]}
```

- Columns: IDX, ID, MSGS, TOOLS, PREVIEW
- ID: abc123
- MSGS: 1
- PREVIEW: "Hello"

### Custom Schema with Integer ID (now works)

```json
{"example_id": 0, "prompt": [{"role": "user", "content": "Hi"}], "completion": [...]}
```

- Columns: IDX, ID, MSGS, PREVIEW (no TOOLS - none detected)
- ID: 0
- MSGS: 2 (from prompt, the detected messages field)
- PREVIEW: "Hi"

### Single Record File (skips list)

```json
{"example_id": 0, "prompt": [...], "completion": [...]}
```

- Skips record list entirely
- Goes directly to comparison/detail view

### Unknown Schema (graceful fallback)

```json
{"data": {"items": [1, 2, 3], "meta": "info"}}
```

- Columns: IDX, PREVIEW (no ID, no MSGS, no TOOLS)
- Shows raw JSON on both sides in comparison view

## Test Cases (`tests/test_dynamic_schema.py`)

### Detection Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_detect_standard_messages` | `{"messages": [...]}` | `mapping.messages == "messages"` |
| `test_detect_custom_messages_field` | `{"dialogue": [{"role": "user", "content": "hi"}]}` | `mapping.messages == "dialogue"` |
| `test_detect_largest_messages_array` | `{"small": [msg], "large": [msg, msg, msg]}` | `mapping.messages == "large"` |
| `test_detect_uuid_by_field_name` | `{"chat_id": "abc", "data": "xyz"}` | `mapping.uuid == "chat_id"` |
| `test_detect_uuid_by_value_format` | `{"ref": "550e8400-e29b-41d4-a716-446655440000"}` | `mapping.uuid == "ref"` |
| `test_detect_uuid_name_priority_over_value` | `{"id": "short", "ref": "550e8400-..."}` | `mapping.uuid == "id"` (name match wins) |
| `test_integer_id_detected` | `{"example_id": 0, "data": "test"}` | `mapping.uuid == "example_id"` |
| `test_no_messages_field` | `{"data": [1, 2, 3]}` | `mapping.messages == None` |

### Content Extraction Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_extract_string_content` | `{"content": "hello"}` | `"hello"` |
| `test_extract_array_content_openai` | `{"content": [{"type": "text", "text": "hi"}]}` | `"hi"` |
| `test_extract_first_user_message` | `[{"role": "system", ...}, {"role": "user", "content": "Q"}]` | `"Q"` |

### Mixin Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_columns_full_mapping` | All fields detected | IDX, ID, MSGS, TOOLS, PREVIEW |
| `test_columns_no_tools` | No tools detected | IDX, ID, MSGS, PREVIEW |
| `test_columns_minimal_mapping` | No fields detected | IDX, PREVIEW |
| `test_configure_table_sets_properties` | Table widget | cursor_type="row", zebra_stripes=True |
| `test_should_skip_single_record` | `[record]` | True |
| `test_should_not_skip_multiple_records` | `[r1, r2]` | False |
| `test_get_record_id_display_truncates` | `{"uuid": "1234567890"}` | "12345678" |
| `test_inheritance_chain` | RecordTableMixin instance | Has methods from DataTableMixin |

### Integration Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_schema_cached_per_file` | Load file twice | Detection only called once |
| `test_mixed_schemas_separate_files` | Two files with different schemas | Each file has correct mapping |
| `test_record_list_columns_match_schema` | Custom schema file | Columns reflect detected fields |
| `test_comparison_raw_mode_fallback` | Unknown schema | Both panels show raw JSON |
| `test_single_record_skips_list` | Single record file | Goes directly to detail view |

## Verification

1. Run existing tests: `pytest tests/test_multiformat_tui.py`
2. Run new tests: `pytest tests/test_dynamic_schema.py`
3. Manual test with standard JSONL file (multi-record)
4. Manual test with single-record file (should skip list)
5. Manual test with custom schema JSON file
6. Verify record list shows correct columns
7. Verify preview extracts correctly
8. Verify schema caching (check detection not repeated per record)
9. Verify comparison mode also skips single-record files
10. Verify inheritance works (RecordTableMixin has DataTableMixin methods)

---

## Assessment Results (Post-Implementation)

### Completed ✓

| Component | Status |
|-----------|--------|
| `detect_messages_field()` | Implemented |
| `detect_uuid_field()` | Implemented |
| `detect_tools_field()` | Implemented |
| `detect_schema()` | Implemented |
| `FieldMapping` dataclass | Implemented |
| Schema caching (`_schema_cache`) | Implemented |
| `DataTableMixin` base class | Implemented |
| `RecordTableMixin` inheritance | Implemented |
| `get_record_summary()` uses FieldMapping | Implemented |
| `dual_record_list_screen.py` dynamic ID extraction | Implemented |
| Single-record skip logic | Implemented |

### Remaining Issues

#### HIGH PRIORITY

| Location | Issue | Fix Required |
|----------|-------|--------------|
| `data_loader.py:751-752` | `load_record_pair_comparison()` uses hardcoded `"uuid"` | Use `get_field_mapping()` for each file |
| `comparison_screen.py:139` | Title generation uses hardcoded `"uuid"` | Use detected ID field with fallback |

#### LOW PRIORITY (Tech Debt)

| Location | Issue |
|----------|-------|
| `record_list.py:58-65` | Unused `COLUMN_TO_FIELD` dict with hardcoded field names |

### Acceptable Fallbacks

These are intentional and do not need fixing:

- `data_table.py:105` - ID field fallback chain (`["uuid", "id", "example_id"...]`)
- `dual_record_list_screen.py:411-412` - `"example_id"` fallback for display label
- `data_loader.py:558-560` - Metadata fields (`license`, `used_in`, `reasoning`)

---

## Fix Plan for Remaining Issues

### Fix 1: `load_record_pair_comparison()`

**File:** `scripts/tui/data_loader.py:751-752`

```python
# Current (hardcoded):
left_uuid = left_record.get("uuid")
right_uuid = right_record.get("uuid")

# Fix (use detected mapping):
left_mapping = get_field_mapping(left_filename) if left_filename else FieldMapping()
right_mapping = get_field_mapping(right_filename) if right_filename else FieldMapping()

left_id_field = left_mapping.uuid or "example_id"
right_id_field = right_mapping.uuid or "example_id"

left_uuid = left_record.get(left_id_field)
right_uuid = right_record.get(right_id_field)
```

### Fix 2: `ComparisonScreen` title

**File:** `scripts/tui/views/comparison_screen.py:139-140`

```python
# Current (hardcoded):
uuid = self._original.get("uuid", "Unknown")
self.title = f"Record {self._record_index}: {uuid}"

# Fix (use detected mapping):
mapping = get_field_mapping(self._filename) if self._filename else FieldMapping()
id_field = mapping.uuid or "example_id"

if id_field in self._original:
    id_value = str(self._original[id_field])[:8]
else:
    id_value = f"idx:{self._record_index}"

self.title = f"Record {self._record_index}: {id_value}"
```

---

## Test Commands

```bash
# Test with standard schema (uuid field)
PYTHONPATH=. uv run python scripts/tui/app.py -c test_comparison/dataset_a/conversations.jsonl test_comparison/dataset_b/conversations.jsonl

# Test with custom schema (example_id field)
PYTHONPATH=. uv run python scripts/tui/app.py -c test_comparison/dataset_a/results_eval.jsonl test_comparison/dataset_b/results_eval.jsonl

# Test comparison mode
PYTHONPATH=. uv run python scripts/tui/app.py test_comparison/dataset_a/results_eval.jsonl
```
