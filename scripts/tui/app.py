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

from textual.app import App
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static, ProgressBar, Footer, Header
from textual.containers import Center, Middle
from textual import work

from scripts.data_formats import detect_format, discover_data_files
from scripts.tui.views.comparison_screen import ComparisonScreen
from scripts.tui.views.file_list import FileListScreen
from scripts.tui.views.record_list import RecordListScreen
from scripts.tui.data_loader import load_all_records, load_records, set_cached_records


class AppMode(Enum):
    """Application mode for single file vs directory."""

    SINGLE_FILE = "single_file"
    DIRECTORY = "directory"


# Maximum file size (in bytes) for synchronous loading (100 MB)
MAX_SYNC_LOAD_SIZE = 100 * 1024 * 1024


class LoadingScreen(Screen):
    """Screen displayed while loading large files."""

    CSS = """
    LoadingScreen {
        align: center middle;
    }

    #loading-container {
        width: 60;
        height: 10;
        border: solid $primary;
        padding: 1 2;
    }

    #loading-text {
        text-align: center;
        margin-bottom: 1;
    }

    #loading-progress {
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self._loaded_count = 0

    def compose(self):
        yield Header()
        with Center():
            with Middle(id="loading-container"):
                yield Static("Loading records...", id="loading-text")
                yield Static("0 records loaded", id="loading-progress")
        yield Footer()

    def update_progress(self, count: int) -> None:
        """Update the loading progress display."""
        self._loaded_count = count
        progress = self.query_one("#loading-progress", Static)
        progress.update(f"{count:,} records loaded")


class ExportingScreen(Screen):
    """Screen displayed while exporting files/records."""

    CSS = """
    ExportingScreen {
        align: center middle;
    }

    #exporting-container {
        width: 60;
        height: 12;
        border: solid $success;
        padding: 1 2;
    }

    #exporting-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #exporting-status {
        text-align: center;
        margin-bottom: 1;
    }

    #exporting-progress {
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, title: str = "Exporting...") -> None:
        super().__init__()
        self._title = title
        self._current = 0
        self._total = 0
        self._current_file = ""

    def compose(self):
        yield Header()
        with Center():
            with Middle(id="exporting-container"):
                yield Static(self._title, id="exporting-title")
                yield Static("Preparing...", id="exporting-status")
                yield Static("", id="exporting-progress")
        yield Footer()

    def update_progress(self, current: int, total: int, current_file: str = "") -> None:
        """Update the export progress display."""
        self._current = current
        self._total = total
        self._current_file = current_file

        status = self.query_one("#exporting-status", Static)
        progress = self.query_one("#exporting-progress", Static)

        if current_file:
            status.update(f"Processing: {current_file}")
        else:
            status.update("Processing...")

        if total > 0:
            progress.update(f"{current} / {total} completed")
        else:
            progress.update(f"{current} completed")

    def set_complete(self, message: str) -> None:
        """Show completion message."""
        status = self.query_one("#exporting-status", Static)
        progress = self.query_one("#exporting-progress", Static)
        title = self.query_one("#exporting-title", Static)

        title.update("Export Complete")
        status.update(message)
        progress.update("Press any key to continue...")


class JsonComparisonApp(App):
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
    ):
        """Initialize the app with a data file or directory.

        Args:
            path: Path to the data file or directory.
            input_format: Format hint ('auto', 'jsonl', 'json', 'parquet').
            is_directory: Whether path is a directory.
            output_dir: Output directory for export operations.
        """
        super().__init__()
        self._path = path
        self._input_format = input_format
        self._is_directory = is_directory
        self._output_dir = output_dir
        self._current_file: str | None = None  # Track selected file in dir mode
        # Backward compatibility
        self.filename = path if not is_directory else ""
        self.records: list[dict] = []
        self._loading = False
        self._file_format: str = "unknown"

    def on_mount(self) -> None:
        """Load data and push the appropriate screen."""
        if self._is_directory:
            # Directory mode - show file picker
            self._load_directory()
        else:
            # Single file mode - load the file directly
            self._load_single_file(self._path)

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
        try:
            file_size = os.path.getsize(filepath)
        except OSError:
            file_size = 0

        if file_size > MAX_SYNC_LOAD_SIZE:
            # Large file - use async loading with progress
            self._loading = True
            self.push_screen(LoadingScreen(filepath))
            self._load_records_async()
        else:
            # Small file - load synchronously
            try:
                self.records = load_all_records(filepath)
                self.push_screen(RecordListScreen())
            except Exception as e:
                self.notify(f"Error loading file: {e}", severity="error")
                # Don't push screen if loading fails

    @work(thread=True)
    def _load_records_async(self) -> None:
        """Load records in a background thread for large files."""
        records: list[dict] = []
        try:
            # Use format-aware loading with schema normalization
            for i, record in enumerate(load_records(self.filename)):
                records.append(record)
                # Update progress every 1000 records
                if i % 1000 == 0:
                    self.call_from_thread(self._update_loading_progress, i + 1)

            # Cache the loaded records
            set_cached_records(self.filename, records)
            self.records = records
            self.call_from_thread(self._loading_complete)
        except Exception as e:
            self.call_from_thread(self._loading_error, str(e))

    def _update_loading_progress(self, count: int) -> None:
        """Update the loading screen progress."""
        try:
            screen = self.screen
            if isinstance(screen, LoadingScreen):
                screen.update_progress(count)
        except Exception:
            pass

    def _loading_complete(self) -> None:
        """Called when async loading is complete."""
        self._loading = False
        self.pop_screen()  # Remove loading screen
        self.push_screen(RecordListScreen())
        self.notify(f"Loaded {len(self.records):,} records")

    def _loading_error(self, error: str) -> None:
        """Called when async loading fails."""
        self._loading = False
        self.notify(f"Error loading file: {error}", severity="error")
        self.pop_screen()  # Remove loading screen
        self.records = []
        self.push_screen(RecordListScreen())

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
        # Load the selected file and show record list
        self._load_single_file(event.file_path)

    def show_comparison(self, index: int) -> None:
        """Push the comparison screen for the selected record.

        Args:
            index: The index of the record to compare.
        """
        self.push_screen(ComparisonScreen(self.filename, index))


def main() -> None:
    """Parse arguments and run the application."""
    parser = argparse.ArgumentParser(
        description="Compare original and processed dataset records in a terminal UI. "
        "Supports JSONL, JSON, and Parquet formats."
    )
    parser.add_argument(
        "path",
        help="Path to data file or directory of data files (JSONL, JSON, or Parquet)"
    )
    parser.add_argument(
        "-O", "--output-dir",
        default="parsed_datasets",
        help="Output directory for export operations (default: parsed_datasets)"
    )
    args = parser.parse_args()

    # Verify the path exists
    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    if not os.access(args.path, os.R_OK):
        print(f"Error: Permission denied: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Determine if path is file or directory
    is_directory = os.path.isdir(args.path)

    app = JsonComparisonApp(
        path=args.path,
        input_format="auto",
        is_directory=is_directory,
        output_dir=args.output_dir,
    )
    app.run()


if __name__ == "__main__":
    main()
