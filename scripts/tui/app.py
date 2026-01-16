"""
Main Textual application for the JSON Comparison Viewer.

This is the entry point for the TUI that compares original JSONL records
with parser_finale processed output side-by-side.
"""

import argparse
import sys

from textual.app import App
from textual.binding import Binding

from scripts.tui.views.record_list import RecordListScreen
from scripts.tui.views.comparison_screen import ComparisonScreen
from scripts.tui.data_loader import load_all_records


class JsonComparisonApp(App):
    """A Textual app for comparing original and processed JSONL records."""

    TITLE = "JSON Comparison Viewer"

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

    def __init__(self, filename: str):
        """Initialize the app with a JSONL file.

        Args:
            filename: Path to the JSONL file to load.
        """
        super().__init__()
        self.filename = filename
        self.records: list[dict] = []

    def on_mount(self) -> None:
        """Load data and push the record list screen."""
        self.records = load_all_records(self.filename)
        self.push_screen(RecordListScreen())

    def on_record_list_screen_record_selected(
        self, message: RecordListScreen.RecordSelected
    ) -> None:
        """Handle record selection from the list screen."""
        self.show_comparison(message.index)

    def show_comparison(self, index: int) -> None:
        """Push the comparison screen for the selected record.

        Args:
            index: The index of the record to compare.
        """
        self.push_screen(ComparisonScreen(self.filename, index))


def main() -> None:
    """Parse arguments and run the application."""
    parser = argparse.ArgumentParser(
        description="Compare original and processed JSONL records in a terminal UI"
    )
    parser.add_argument(
        "filename",
        help="Path to the JSONL file to explore"
    )
    args = parser.parse_args()

    # Verify the file exists
    try:
        with open(args.filename, 'r') as f:
            pass
    except FileNotFoundError:
        print(f"Error: File not found: {args.filename}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied: {args.filename}", file=sys.stderr)
        sys.exit(1)

    app = JsonComparisonApp(args.filename)
    app.run()


if __name__ == "__main__":
    main()
