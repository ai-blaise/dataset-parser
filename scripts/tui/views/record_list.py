"""
Record List Screen for JSONL Dataset Explorer.

Displays a list of JSONL records in a DataTable with navigation and selection.
Supports both row selection (Enter for full record) and cell selection (click for field detail).
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header

from scripts.tui.data_loader import load_all_records, get_record_summary, truncate
from scripts.tui.views.field_detail import FieldDetailScreen


class RecordListScreen(Screen):
    """Screen that displays a list of JSONL records in a DataTable."""

    CSS = """
    RecordListScreen {
        layout: vertical;
    }

    DataTable {
        height: 1fr;
        border: solid $primary;
    }

    DataTable > .datatable--header {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $secondary;
        color: $text;
    }

    DataTable > .datatable--hover {
        background: $primary-darken-2;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "select_record", "View Record"),
        Binding("f", "show_field_detail", "Field Detail"),
    ]

    # Column key to field name mapping
    COLUMN_TO_FIELD: dict[str, str] = {
        "idx": "index",
        "uuid": "uuid",
        "msgs": "messages",
        "tools": "tools",
        "license": "license",
        "used_in": "used_in",
        "rsn": "reasoning",
        "preview": "preview",
    }

    class RecordSelected(Message):
        """Message posted when a record is selected."""

        def __init__(self, index: int, record: dict) -> None:
            self.index = index
            self.record = record
            super().__init__()

    def __init__(
        self,
        filename: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the RecordListScreen.

        Args:
            filename: Path to the JSONL file to load. If None, will try to get from app.
            name: Optional name for the screen.
            id: Optional ID for the screen.
            classes: Optional CSS classes for the screen.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._filename = filename
        self._records: list[dict] = []

    @property
    def filename(self) -> str | None:
        """Get the filename, either from constructor or app."""
        if self._filename:
            return self._filename
        # Try to get from app if available
        if hasattr(self.app, 'filename'):
            return self.app.filename
        return None

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        yield DataTable(id="record-table", cursor_type="cell")
        yield Footer()

    def on_mount(self) -> None:
        """Load data and populate the table when screen is mounted."""
        self.title = "JSONL Dataset Explorer"
        self._load_data()

    def _load_data(self) -> None:
        """Load JSONL data and populate the DataTable."""
        table = self.query_one("#record-table", DataTable)

        # Add columns
        table.add_column("IDX", key="idx", width=6)
        table.add_column("UUID", key="uuid", width=15)
        table.add_column("MSGS", key="msgs", width=5)
        table.add_column("TOOLS", key="tools", width=6)
        table.add_column("LICENSE", key="license", width=12)
        table.add_column("USED_IN", key="used_in", width=10)
        table.add_column("RSN", key="rsn", width=4)
        table.add_column("PREVIEW", key="preview")

        # Load records
        filename = self.filename
        if not filename:
            table.add_row("--", "No file specified", "--", "--", "--", "--", "--", "--")
            return

        try:
            self._records = load_all_records(filename)
        except FileNotFoundError:
            table.add_row("--", f"File not found: {filename}", "--", "--", "--", "--", "--", "--")
            return
        except Exception as e:
            table.add_row("--", f"Error: {e}", "--", "--", "--", "--", "--", "--")
            return

        # Populate table with record summaries
        for idx, record in enumerate(self._records):
            summary = get_record_summary(record, idx)

            # Format reasoning field as "on" or "-"
            rsn_display = "on" if summary['reasoning'] != '-' else "-"

            # Truncate fields for display
            license_display = truncate(str(summary['license']), 10)
            used_in_display = truncate(str(summary['used_in']), 8)
            preview_display = summary['preview']

            table.add_row(
                str(summary['index']),
                summary['uuid'],
                str(summary['msg_count']),
                str(summary['tool_count']),
                license_display,
                used_in_display,
                rsn_display,
                preview_display,
                key=str(idx),
            )

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_select_record(self) -> None:
        """Handle Enter key to select the current record."""
        table = self.query_one("#record-table", DataTable)

        if not self._records:
            return

        # Get the currently highlighted row from cursor coordinate
        cursor_coord = table.cursor_coordinate
        if cursor_coord is None:
            return

        row_idx = cursor_coord.row
        if row_idx < 0 or row_idx >= len(self._records):
            return

        record = self._records[row_idx]

        # Post message for parent/app to handle navigation
        self.post_message(self.RecordSelected(index=row_idx, record=record))

    def action_show_field_detail(self) -> None:
        """Handle 'f' key to show field detail for current cell."""
        table = self.query_one("#record-table", DataTable)

        if not self._records:
            return

        cursor_coord = table.cursor_coordinate
        if cursor_coord is None:
            return

        row_idx = cursor_coord.row
        col_idx = cursor_coord.column

        if row_idx < 0 or row_idx >= len(self._records):
            return

        record = self._records[row_idx]

        # Get column key from index
        column_key = self._get_column_key_at(table, col_idx)
        if column_key is None:
            return

        field_name = self.COLUMN_TO_FIELD.get(column_key, column_key)
        self.app.push_screen(FieldDetailScreen(field_name, record, row_idx))

    def _get_column_key_at(self, table: DataTable, col_idx: int) -> str | None:
        """Get the column key at a given column index."""
        columns = list(table.columns.keys())
        if 0 <= col_idx < len(columns):
            return str(columns[col_idx])
        return None

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection (click) to show field detail."""
        if not self._records:
            return

        table = self.query_one("#record-table", DataTable)
        row_idx = event.coordinate.row
        col_idx = event.coordinate.column

        if row_idx < 0 or row_idx >= len(self._records):
            return

        record = self._records[row_idx]

        # Get column key from index
        column_key = self._get_column_key_at(table, col_idx)
        if column_key is None:
            return

        field_name = self.COLUMN_TO_FIELD.get(column_key, column_key)
        self.app.push_screen(FieldDetailScreen(field_name, record, row_idx))

    def get_record(self, index: int) -> dict | None:
        """Get a record by index.

        Args:
            index: The record index.

        Returns:
            The record dict or None if index is out of range.
        """
        if 0 <= index < len(self._records):
            return self._records[index]
        return None

    @property
    def record_count(self) -> int:
        """Return the number of loaded records."""
        return len(self._records)
