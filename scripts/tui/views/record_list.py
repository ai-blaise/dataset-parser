"""
Record List Screen for JSON Comparison Viewer.

Displays a list of JSONL records in a DataTable with navigation and selection.
Select a record with Enter to open the comparison view.
"""

from __future__ import annotations

from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header

from scripts.tui.data_loader import export_records, get_record_summary
from scripts.parser_finale import process_record


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
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "go_back", "Back", show=True),
        Binding("b", "go_back", "Back", show=False),
        Binding("X", "export_all", "Export All"),
    ]

    # Column key to field name mapping
    COLUMN_TO_FIELD: dict[str, str] = {
        "idx": "index",
        "uuid": "uuid",
        "msgs": "messages",
        "tools": "tools",
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
        yield DataTable(id="record-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        """Load data and populate the table when screen is mounted."""
        self.title = "JSON Comparison Viewer - Select Record"
        self._load_data()

    def _load_data(self) -> None:
        """Load JSONL data and populate the DataTable."""
        table = self.query_one("#record-table", DataTable)

        # Add columns (simplified for comparison view)
        table.add_column("IDX", key="idx", width=6)
        table.add_column("UUID", key="uuid", width=15)
        table.add_column("MSGS", key="msgs", width=6)
        table.add_column("TOOLS", key="tools", width=6)
        table.add_column("PREVIEW", key="preview")

        # Use records from app (already loaded and cached)
        if hasattr(self.app, 'records') and self.app.records:
            self._records = self.app.records
        else:
            # Fallback: no records available
            table.add_row("--", "No records loaded", "--", "--", "--")
            return

        if not self._records:
            table.add_row("--", "No records found", "--", "--", "--")
            return

        # Populate table with record summaries
        for idx, record in enumerate(self._records):
            summary = get_record_summary(record, idx)

            table.add_row(
                str(summary['index']),
                summary['uuid'],
                str(summary['msg_count']),
                str(summary['tool_count']),
                summary['preview'],
                key=str(idx),
            )

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_go_back(self) -> None:
        """Go back to file list (directory mode) or quit."""
        self.app.pop_screen()

    def action_export_all(self) -> None:
        """Export all records (processed) to the output directory."""
        if not self._records:
            self.notify("No records to export", severity="warning")
            return

        # Import here to avoid circular imports
        from scripts.tui.app import ExportingScreen

        # Push the exporting screen
        exporting_screen = ExportingScreen(title="Exporting Records...")
        self.app.push_screen(exporting_screen)

        # Start the background export
        self._run_export_all_records(exporting_screen)

    @work(thread=True)
    def _run_export_all_records(self, exporting_screen: "ExportingScreen") -> None:
        """Run the export in a background thread."""
        output_dir = getattr(self.app, "_output_dir", None)
        if not output_dir:
            output_dir = "parsed_datasets"

        total_records = len(self._records)
        processed_records = []

        try:
            # Process all records with progress updates
            for i, record in enumerate(self._records):
                self.app.call_from_thread(
                    exporting_screen.update_progress,
                    i,
                    total_records,
                    f"Record {i + 1}",
                )
                processed_records.append(process_record(record))

            # Get filename from app
            source_filename = getattr(self.app, "filename", "records")

            # Final update before writing
            self.app.call_from_thread(
                exporting_screen.update_progress,
                total_records,
                total_records,
                "Writing to file...",
            )

            output_path = export_records(
                records=processed_records,
                output_dir=output_dir,
                source_filename=source_filename,
                format="json",
            )

            message = f"Exported {len(processed_records)} records to {output_path}"
            self.app.call_from_thread(exporting_screen.set_complete, message)

        except Exception as e:
            self.app.call_from_thread(
                exporting_screen.set_complete,
                f"Export failed: {e}",
            )

        # Pop the screen after a short delay to show completion
        import time
        time.sleep(1.5)
        self.app.call_from_thread(self.app.pop_screen)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection from the DataTable (Enter key press)."""
        if not self._records:
            return

        # The row key is the string index we set when adding rows
        row_key = event.row_key
        if row_key is None:
            return

        try:
            row_idx = int(row_key.value)
        except (ValueError, TypeError):
            return

        if row_idx < 0 or row_idx >= len(self._records):
            return

        record = self._records[row_idx]

        # Post message for parent/app to handle navigation
        self.post_message(self.RecordSelected(index=row_idx, record=record))

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
