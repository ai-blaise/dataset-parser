"""
Dual Pane Comparison Screen with fully independent navigation.

Each pane has its own state: FILE_LIST → RECORD_LIST → JSON_VIEW
Panes are completely independent - no reliance on each other.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from scripts.data_formats import discover_data_files, format_file_size
from scripts.tui.data_loader import (
    FieldMapping,
    get_field_mapping,
    get_record_count,
    get_record_summary,
    load_all_records,
    load_records,
)
from scripts.tui.mixins import (
    BackgroundTaskMixin,
    DualPaneMixin,
    RecordTableMixin,
    VimNavigationMixin,
)
from scripts.tui.widgets.json_tree_panel import JsonTreePanel


class PaneState(Enum):
    """State of a single pane."""

    FILE_LIST = "file_list"
    RECORD_LIST = "record_list"
    JSON_VIEW = "json_view"


class DualRecordListScreen(
    BackgroundTaskMixin, DualPaneMixin, RecordTableMixin, VimNavigationMixin, Screen
):
    """Two independent panes, each with FILE_LIST → RECORD_LIST → JSON_VIEW flow."""

    CSS_PATH = "../styles/base.tcss"

    CSS = """
    DualRecordListScreen {
        layout: vertical;
    }

    #dual-header {
        background: $primary-background;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    #dual-container {
        height: 1fr;
    }

    #left-panel, #right-panel {
        height: 100%;
    }

    #left-panel {
        background: $primary 10%;
    }

    #right-panel {
        background: $success 10%;
    }

    .file-table, .record-table {
        height: 1fr;
    }

    .json-tree {
        height: 1fr;
    }

    Header { dock: top; }
    Footer { dock: bottom; }
    """

    # All dual-pane bindings (vim navigation + panel switching)
    BINDINGS = DualPaneMixin.DUAL_PANE_BINDINGS

    def __init__(
        self,
        left_dir: str,
        right_dir: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._left_dir = left_dir
        self._right_dir = right_dir

        # Left pane state
        self._left_state: PaneState = PaneState.FILE_LIST
        self._left_files: list[dict] = []
        self._left_selected_file: str | None = None
        self._left_records: list[dict[str, Any]] = []
        self._left_selected_index: int | None = None
        self._left_selected_record: dict[str, Any] | None = None

        # Right pane state
        self._right_state: PaneState = PaneState.FILE_LIST
        self._right_files: list[dict] = []
        self._right_selected_file: str | None = None
        self._right_records: list[dict[str, Any]] = []
        self._right_selected_index: int | None = None
        self._right_selected_record: dict[str, Any] | None = None

        # Track which side is currently loading (for async callback)
        self._loading_side: str = "left"

    def compose(self) -> ComposeResult:
        import os

        left_basename = os.path.basename(self._left_dir)
        right_basename = os.path.basename(self._right_dir)

        yield Header()
        yield Static("Dataset Comparison - Independent Panes", id="dual-header")
        with Horizontal(id="dual-container"):
            with Vertical(id="left-panel", classes="active"):
                yield Static(
                    f"Left: {left_basename}/", id="left-header", classes="panel-header"
                )
                yield DataTable(
                    id="left-file-table", classes="file-table", cursor_type="row"
                )
                yield DataTable(
                    id="left-record-table", classes="record-table", cursor_type="row"
                )
                yield JsonTreePanel(label="left", id="left-tree", classes="json-tree")
            with Vertical(id="right-panel", classes="inactive"):
                yield Static(
                    f"Right: {right_basename}/",
                    id="right-header",
                    classes="panel-header",
                )
                yield DataTable(
                    id="right-file-table", classes="file-table", cursor_type="row"
                )
                yield DataTable(
                    id="right-record-table", classes="record-table", cursor_type="row"
                )
                yield JsonTreePanel(label="right", id="right-tree", classes="json-tree")
        yield Footer()

    def on_mount(self) -> None:
        # Load files for both directories
        self._left_files = discover_data_files(self._left_dir)
        self._right_files = discover_data_files(self._right_dir)

        # Populate file tables
        self._populate_file_table("left")
        self._populate_file_table("right")

        # Refresh display
        self._refresh_pane("left")
        self._refresh_pane("right")
        self._update_panel_styles()
        self._focus_active_widget()

    def _populate_file_table(self, side: str) -> None:
        """Populate file table for a pane."""
        table = self.query_one(f"#{side}-file-table", DataTable)
        files = self._left_files if side == "left" else self._right_files

        table.add_column("FILE NAME", width=40)
        table.add_column("FORMAT", width=10)
        table.add_column("SIZE", width=12)

        for file_info in files:
            table.add_row(
                file_info["name"],
                file_info["format"].upper(),
                format_file_size(file_info["size"]),
                key=file_info["path"],
            )
        table.zebra_stripes = True

    def _populate_pane_records(self, side: str) -> None:
        """Populate record table for a pane using RecordTableMixin."""
        table = self.query_one(f"#{side}-record-table", DataTable)
        records = self._left_records if side == "left" else self._right_records
        selected_file = (
            self._left_selected_file if side == "left" else self._right_selected_file
        )

        # Get field mapping for dynamic columns
        mapping = get_field_mapping(selected_file) if selected_file else FieldMapping()

        # Use mixin method for consistent behavior
        self._populate_record_table(table, records, mapping)

    def _refresh_pane(self, side: str) -> None:
        """Update visibility based on pane state."""
        import os

        state = self._left_state if side == "left" else self._right_state

        file_table = self.query_one(f"#{side}-file-table", DataTable)
        record_table = self.query_one(f"#{side}-record-table", DataTable)
        tree = self.query_one(f"#{side}-tree", JsonTreePanel)
        header = self.query_one(f"#{side}-header", Static)

        directory = self._left_dir if side == "left" else self._right_dir
        dir_basename = os.path.basename(directory)

        # Hide all first
        file_table.display = False
        record_table.display = False
        tree.display = False

        if state == PaneState.FILE_LIST:
            file_table.display = True
            header.update(f"{side.capitalize()}: {dir_basename}/")
        elif state == PaneState.RECORD_LIST:
            record_table.display = True
            selected_file = (
                self._left_selected_file
                if side == "left"
                else self._right_selected_file
            )
            file_basename = os.path.basename(selected_file) if selected_file else "?"
            records = self._left_records if side == "left" else self._right_records
            header.update(
                f"{side.capitalize()}: {file_basename} [{len(records)} records]"
            )
        else:  # JSON_VIEW
            tree.display = True
            selected_file = (
                self._left_selected_file
                if side == "left"
                else self._right_selected_file
            )
            file_basename = os.path.basename(selected_file) if selected_file else "?"
            idx = (
                self._left_selected_index
                if side == "left"
                else self._right_selected_index
            )
            header.update(f"{side.capitalize()}: {file_basename} [#{idx}]")

    def _focus_active_widget(self) -> None:
        """Focus the appropriate widget in the active panel."""
        side = self._active_panel
        state = self._left_state if side == "left" else self._right_state

        if state == PaneState.FILE_LIST:
            self.query_one(f"#{side}-file-table", DataTable).focus()
        elif state == PaneState.RECORD_LIST:
            self.query_one(f"#{side}-record-table", DataTable).focus()
        else:
            self.query_one(f"#{side}-tree", JsonTreePanel).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter on any DataTable."""
        table_id = event.data_table.id

        # Determine side and table type
        if table_id == "left-file-table":
            self._handle_file_selected("left", event)
        elif table_id == "right-file-table":
            self._handle_file_selected("right", event)
        elif table_id == "left-record-table":
            self._handle_record_selected("left", event)
        elif table_id == "right-record-table":
            self._handle_record_selected("right", event)

    def _handle_file_selected(self, side: str, event: DataTable.RowSelected) -> None:
        """Handle file selection - transition to RECORD_LIST."""
        import os

        file_path = str(event.row_key.value)
        file_basename = os.path.basename(file_path)

        # Store the selected file path and side for use in callbacks
        if side == "left":
            self._left_selected_file = file_path
        else:
            self._right_selected_file = file_path

        # Store which side is loading for the callback
        self._loading_side = side

        # Check file size and use async loading for large files
        if self.should_load_async(file_path):
            # Large file - use async loading with progress
            # Get total count for progress display
            try:
                total = get_record_count(file_path)
            except Exception:
                total = None
            self._run_loading_task(
                filename=file_basename,
                load_fn=lambda: load_records(file_path),
                on_complete=self._on_pane_records_loaded,
                on_error=self._on_pane_loading_error,
                total_count=total,
            )
        else:
            # Small file - load synchronously
            try:
                records = load_all_records(file_path)
                self._complete_file_load(side, records)
            except Exception as e:
                self.notify(f"Error loading: {e}", severity="error")

    def _complete_file_load(self, side: str, records: list[dict[str, Any]]) -> None:
        """Complete the file loading process after records are loaded.

        Uses inherited _should_skip_table() to determine if we
        should skip directly to JSON_VIEW for single-record files.
        """
        # Update records for this pane
        if side == "left":
            self._left_records = records
        else:
            self._right_records = records

        # Use inherited method to check if we should skip record list
        if self._should_skip_table(records):
            # Single record - skip to JSON_VIEW directly
            record = records[0]
            if side == "left":
                self._left_selected_index = 0
                self._left_selected_record = record
                self._left_state = PaneState.JSON_VIEW
            else:
                self._right_selected_index = 0
                self._right_selected_record = record
                self._right_state = PaneState.JSON_VIEW

            # Load JSON into tree, use mixin for ID display
            tree = self.query_one(f"#{side}-tree", JsonTreePanel)
            id_display = self._get_record_id_display(record)
            tree.load_json(record, label=f"Record 0 ({id_display})")
        else:
            # Multiple records - show record list
            if side == "left":
                self._left_state = PaneState.RECORD_LIST
            else:
                self._right_state = PaneState.RECORD_LIST
            self._populate_pane_records(side)

        self._refresh_pane(side)
        self._focus_active_widget()

    def _on_pane_records_loaded(self, records: list[dict[str, Any]]) -> None:
        """Called when async loading completes for a pane."""
        side = getattr(self, "_loading_side", "left")
        self._complete_file_load(side, records)
        self.notify(f"Loaded {len(records):,} records")

    def _on_pane_loading_error(self, error: str) -> None:
        """Called when async loading fails for a pane."""
        self.notify(f"Error loading: {error}", severity="error")

    def _handle_record_selected(self, side: str, event: DataTable.RowSelected) -> None:
        """Handle record selection - transition to JSON_VIEW."""
        row_key = event.row_key
        if row_key is None:
            return

        try:
            idx = int(row_key.value)
        except (ValueError, TypeError, AttributeError):
            return

        records = self._left_records if side == "left" else self._right_records
        if idx < 0 or idx >= len(records):
            return

        record = records[idx]

        # Update state for this pane only
        if side == "left":
            self._left_selected_index = idx
            self._left_selected_record = record
            self._left_state = PaneState.JSON_VIEW
        else:
            self._right_selected_index = idx
            self._right_selected_record = record
            self._right_state = PaneState.JSON_VIEW

        # Load JSON
        tree = self.query_one(f"#{side}-tree", JsonTreePanel)
        selected_file = (
            self._left_selected_file if side == "left" else self._right_selected_file
        )
        mapping = get_field_mapping(selected_file) if selected_file else FieldMapping()

        # Get ID from detected field, with fallback chain
        id_value = None
        if mapping.uuid and mapping.uuid in record:
            id_value = str(record[mapping.uuid])[:8]
        elif "example_id" in record:
            id_value = str(record["example_id"])
        else:
            id_value = f"idx:{idx}"

        tree.load_json(record, label=f"Record {idx} ({id_value})")

        self._refresh_pane(side)
        self._focus_active_widget()

    def action_go_back(self) -> None:
        """Go back one step in the active pane."""
        side = self._active_panel
        state = self._left_state if side == "left" else self._right_state

        if state == PaneState.JSON_VIEW:
            # JSON → Record list
            if side == "left":
                self._left_state = PaneState.RECORD_LIST
                self._left_selected_record = None
            else:
                self._right_state = PaneState.RECORD_LIST
                self._right_selected_record = None
            self._refresh_pane(side)
            self._focus_active_widget()
        elif state == PaneState.RECORD_LIST:
            # Record list → File list
            if side == "left":
                self._left_state = PaneState.FILE_LIST
                self._left_selected_file = None
                self._left_records = []
            else:
                self._right_state = PaneState.FILE_LIST
                self._right_selected_file = None
                self._right_records = []
            self._refresh_pane(side)
            self._focus_active_widget()
        else:
            # File list → Exit screen
            self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
