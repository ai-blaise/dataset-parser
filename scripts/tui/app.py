"""
Main Textual application for the JSONL Dataset Explorer.

This is the entry point for the TUI dataset explorer.
"""

import argparse
import sys

from textual.app import App
from textual.binding import Binding

from scripts.tui.views.record_list import RecordListScreen
from scripts.tui.views.record_detail import RecordDetailScreen
from scripts.tui.data_loader import load_all_records


class DatasetExplorerApp(App):
    """A Textual app to explore JSONL datasets."""

    TITLE = "JSONL Dataset Explorer"

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

    .record-detail {
        padding: 1 2;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        padding: 1;
    }

    .metadata-container {
        padding: 1 2;
        background: $surface-darken-1;
        border: solid $primary;
    }

    .metadata-label {
        color: $text-muted;
        text-style: bold;
    }

    .metadata-value {
        color: $text;
    }

    .message-container {
        margin-bottom: 1;
        padding: 1;
        border: solid $primary-darken-2;
    }

    .role-system {
        background: $warning-darken-3;
        color: $text;
    }

    .role-user {
        background: $success-darken-3;
        color: $text;
    }

    .role-assistant {
        background: $primary-darken-2;
        color: $text;
    }

    .role-tool {
        background: $secondary-darken-2;
        color: $text;
    }

    .tool-call {
        background: $accent-darken-2;
        padding: 1;
        margin: 1 0;
        border: dashed $accent;
    }

    .reasoning-content {
        background: $warning-darken-2;
        padding: 1;
        margin: 1 0;
        border: solid $warning;
        color: $text;
    }

    .tool-schema {
        background: $surface-darken-1;
        padding: 1;
        margin: 1 0;
        border: solid $secondary;
    }

    Static {
        width: 100%;
    }

    #record-header {
        dock: top;
        height: 3;
        padding: 1;
        background: $primary-darken-1;
        text-style: bold;
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
        """Load data and push the initial screen."""
        self.records = load_all_records(self.filename)
        self.push_screen(RecordListScreen())

    def on_record_list_screen_record_selected(
        self, message: RecordListScreen.RecordSelected
    ) -> None:
        """Handle record selection from the list screen."""
        self.show_record_detail(message.record, message.index)

    def show_record_detail(self, record: dict, index: int) -> None:
        """Push the record detail screen for the selected record.

        Args:
            record: The full record dictionary to display.
            index: The index of the record in the dataset.
        """
        self.push_screen(RecordDetailScreen(record, index))


def main() -> None:
    """Parse arguments and run the application."""
    parser = argparse.ArgumentParser(
        description="Explore JSONL datasets in a terminal UI"
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

    app = DatasetExplorerApp(args.filename)
    app.run()


if __name__ == "__main__":
    main()
