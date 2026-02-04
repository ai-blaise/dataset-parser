"""
Main Textual application for the Dataset Viewer.

This is the entry point for the TUI that compares original dataset records
with parser_finale processed output side-by-side.

Supported Formats:
    - JSONL (.jsonl): One JSON object per line
    - JSON (.json): Array of JSON objects
    - Parquet (.parquet, .pq): Apache Parquet columnar format
"""

import argparse
import os
import sys
from enum import Enum
from typing import Any

from textual.app import App
from textual.binding import Binding

from scripts.data_formats import detect_format, discover_data_files
from scripts.tui.data_loader import get_record_count, load_all_records, load_records, set_cached_records
from scripts.tui.mixins import BackgroundTaskMixin
from scripts.tui.screens import ExportingScreen, LoadingScreen
from scripts.tui.views.comparison_screen import ComparisonScreen
from scripts.tui.views.file_list import FileListScreen
from scripts.tui.views.record_list import RecordListScreen


class AppMode(Enum):
    """Application mode for single file vs directory vs comparison."""

    SINGLE_FILE = "single_file"
    DIRECTORY = "directory"
    COMPARISON = "comparison"


class JsonComparisonApp(BackgroundTaskMixin, App):
    """A Textual app for comparing original and processed dataset records."""

    TITLE = "Dataset Viewer"

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
    }

    Footer {
        dock: bottom;
        height: 1;
        background: $primary-darken-2;
    }

    /* DataTable styling for record list */
    DataTable {
        height: 100%;
        background: $surface;
    }

    DataTable > .datatable--header {
        background: $primary-darken-1;
        color: $text;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $secondary;
        color: $text;
    }

    DataTable > .datatable--hover {
        background: $primary-lighten-1;
    }

    /* Comparison screen layout */
    #comparison-container {
        height: 1fr;
    }

    #left-panel, #right-panel {
        width: 50%;
        border: solid $primary;
        padding: 0 1;
    }

    #left-panel {
        border-right: none;
    }

    .panel-header {
        dock: top;
        height: 3;
        background: $surface;
        border-bottom: solid $primary;
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    #left-tree, #right-tree {
        height: 1fr;
    }

    /* Diff highlighting */
    .diff-added {
        background: $success 20%;
    }

    .diff-removed {
        background: $error 20%;
    }

    .diff-changed {
        background: $warning 20%;
    }

    .diff-unchanged {
        /* Default styling, no change */
    }

    /* Tree styling */
    Tree {
        background: $surface;
        padding: 1;
    }

    Tree > .tree--cursor {
        background: $secondary;
    }

    Tree > .tree--guides {
        color: $text-muted;
    }

    Static {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(
        self,
        path: str,
        input_format: str = "auto",
        is_directory: bool = False,
        output_dir: str | None = None,
        compare_path: str | None = None,
        is_compare_directory: bool = False,
    ):
        """Initialize the app with a data file or directory.

        Args:
            path: Path to the data file or directory.
            input_format: Format hint ('auto', 'jsonl', 'json', 'parquet').
            is_directory: Whether path is a directory.
            output_dir: Output directory for export operations.
            compare_path: Path to second dataset for comparison mode.
            is_compare_directory: Whether compare_path is a directory.
        """
        super().__init__()
        self._path = path
        self._input_format = input_format
        self._is_directory = is_directory
        self._output_dir = output_dir
        self._current_file: str | None = None
        self.filename = path if not is_directory else ""
        self.records: list[dict] = []
        self._loading = False
        self._file_format: str = "unknown"

        # Comparison mode fields
        self._compare_path = compare_path
        self._is_compare_directory = is_compare_directory
        self._compare_records: list[dict] = []
        self._compare_left_file: str | None = None
        self._compare_right_file: str | None = None
        self._compare_left_index: int = 0

    def on_mount(self) -> None:
        """Load data and push the appropriate screen based on mode."""
        if self._compare_path:
            self.mode = AppMode.COMPARISON
            self._setup_comparison_mode()
        elif self._is_directory:
            self.mode = AppMode.DIRECTORY
            self._load_directory()
        else:
            self.mode = AppMode.SINGLE_FILE
            self._load_single_file(self._path)

    def _setup_comparison_mode(self) -> None:
        """Set up comparison mode - requires both paths to be directories."""
        if not self._is_directory or not self._is_compare_directory:
            self.notify(
                "Comparison mode requires both paths to be directories",
                severity="error",
            )
            return
        self._load_comparison_directory()

    def _load_comparison_directory(self) -> None:
        """Load directories and push DualRecordListScreen with independent panes."""
        from scripts.tui.views.dual_record_list_screen import DualRecordListScreen

        if not self._compare_path:
            self.notify("No comparison path specified", severity="error")
            return

        if not os.path.isdir(self._path):
            self.notify(f"Left path is not a directory: {self._path}", severity="error")
            return
        if not os.path.isdir(self._compare_path):
            self.notify(
                f"Right path is not a directory: {self._compare_path}", severity="error"
            )
            return

        left_basename = os.path.basename(self._path)
        right_basename = os.path.basename(self._compare_path)
        self.title = f"Dataset Comparison - {left_basename} ↔ {right_basename}"

        self.push_screen(DualRecordListScreen(self._path, self._compare_path))

    def on_record_list_screen_record_selected(
        self, message: RecordListScreen.RecordSelected
    ) -> None:
        """Handle record selection from the list screen."""
        self.show_comparison(message.index)

    def on_file_list_screen_file_selected(
        self, event: FileListScreen.FileSelected
    ) -> None:
        """Handle file selection from directory listing."""
        self._current_file = event.file_path
        self._load_single_file(event.file_path)

    def show_comparison(self, index: int) -> None:
        """Push the comparison screen for the selected record."""
        filename = self.filename or ""
        self.push_screen(ComparisonScreen(filename, index))

    def _load_directory(self) -> None:
        """Load directory and show file list."""
        files = discover_data_files(self._path)
        if not files:
            self.exit(message=f"No supported files found in {self._path}")
            return

        self.title = f"Dataset Viewer - {os.path.basename(self._path)}/"
        self.push_screen(FileListScreen(self._path, files))

    def _load_single_file(self, filepath: str) -> None:
        """Load a single file and show record list."""
        self.filename = filepath
        self._current_file = filepath

        # Detect file format and update title
        try:
            self._file_format = detect_format(filepath)
        except ValueError as e:
            self.notify(f"Unsupported file format: {e}", severity="error")
            return  # Don't push screen if format detection fails

        # Update title to show format
        basename = os.path.basename(filepath)
        self.title = f"Dataset Viewer - {basename} ({self._file_format})"

        # Check file size to decide loading strategy
        if self.should_load_async(filepath):
            # Large file - use async loading with progress
            self._loading = True
            # Get total count for progress display
            try:
                total = get_record_count(filepath)
            except Exception:
                total = None
            self._run_loading_task(
                filename=basename,
                load_fn=lambda: load_records(filepath),
                on_complete=self._on_records_loaded,
                on_error=self._on_loading_error,
                total_count=total,
            )
        else:
            # Small file - load synchronously
            try:
                self.records = load_all_records(filepath)
                self._push_appropriate_screen()
            except Exception as e:
                self.notify(f"Error loading file: {e}", severity="error")

    def _on_records_loaded(self, records: list[dict[str, Any]]) -> None:
        """Called when async loading completes successfully."""
        self._loading = False
        set_cached_records(self.filename, records)
        self.records = records
        self._push_appropriate_screen()
        self.notify(f"Loaded {len(self.records):,} records")

    def _push_appropriate_screen(self) -> None:
        """Push RecordListScreen or ComparisonScreen based on record count.

        If there's only 1 record, skip the record list and go directly
        to the comparison view. Otherwise show the record list for selection.
        """
        if len(self.records) == 1:
            # Single record - go straight to comparison view
            self.push_screen(ComparisonScreen(self.filename, 0))
        else:
            # Multiple records - show record list for selection
            self.push_screen(RecordListScreen())

    def _on_loading_error(self, error: str) -> None:
        """Called when async loading fails."""
        self._loading = False
        self.notify(f"Error loading file: {error}", severity="error")
        self.records = []
        self.push_screen(RecordListScreen())


def main() -> None:
    """Parse arguments and run the application."""
    parser = argparse.ArgumentParser(
        description="Compare original and processed dataset records in a terminal UI. "
        "Supports JSONL, JSON, and Parquet formats."
    )
    parser.add_argument(
        "path",
        help="Path to data file or directory of data files (JSONL, JSON, or Parquet)",
    )
    parser.add_argument(
        "-O",
        "--output-dir",
        default="parsed_datasets",
        help="Output directory for export operations (default: parsed_datasets)",
    )
    parser.add_argument(
        "--compare",
        "-c",
        dest="compare_path",
        default=None,
        help="Path to second dataset for side-by-side comparison",
    )
    args = parser.parse_args()

    # Verify the path exists
    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    if not os.access(args.path, os.R_OK):
        print(f"Error: Permission denied: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Verify compare path exists if provided
    if args.compare_path:
        if not os.path.exists(args.compare_path):
            print(
                f"Error: Compare path not found: {args.compare_path}", file=sys.stderr
            )
            sys.exit(1)

        if not os.access(args.compare_path, os.R_OK):
            print(
                f"Error: Compare path permission denied: {args.compare_path}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Determine if path is file or directory
    is_directory = os.path.isdir(args.path)
    is_compare_directory = (
        os.path.isdir(args.compare_path) if args.compare_path else False
    )

    app = JsonComparisonApp(
        path=args.path,
        input_format="auto",
        is_directory=is_directory,
        output_dir=args.output_dir,
        compare_path=args.compare_path,
        is_compare_directory=is_compare_directory,
    )
    app.run()


if __name__ == "__main__":
    main()
