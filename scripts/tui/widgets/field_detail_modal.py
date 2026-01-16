"""Modal screen for displaying full field content."""

import json
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class FieldDetailModal(ModalScreen[None]):
    """A modal screen that displays the full content of a JSON field."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close"),
        Binding("q", "quit", "Quit App"),
    ]

    CSS = """
    FieldDetailModal {
        align: center middle;
    }

    FieldDetailModal > Vertical {
        width: 80%;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    FieldDetailModal .modal-header {
        dock: top;
        height: auto;
        padding: 1 2;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
    }

    FieldDetailModal .field-key-label {
        dock: top;
        height: auto;
        padding: 1 2;
        background: $surface-darken-1;
        color: $secondary;
        text-style: bold;
    }

    FieldDetailModal .content-container {
        height: 1fr;
        padding: 1 2;
        background: $surface-darken-2;
    }

    FieldDetailModal .field-content {
        width: 100%;
        height: auto;
        padding: 0;
    }

    FieldDetailModal .close-hint {
        dock: bottom;
        height: auto;
        padding: 1 2;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        field_key: str,
        field_value: Any,
        panel_label: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the field detail modal.

        Args:
            field_key: The JSON key (e.g., "content" or "role").
            field_value: The full value - could be string, dict, list, etc.
            panel_label: Either "ORIGINAL JSONL" or "PARSER_FINALE OUTPUT".
            name: Optional name for the widget.
            id: Optional ID for the widget.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self.field_key = field_key
        self.field_value = field_value
        self.panel_label = panel_label

    def _format_value(self, value: Any) -> str:
        """Format the value for display.

        Args:
            value: The value to format.

        Returns:
            A formatted string representation.
        """
        if isinstance(value, str):
            # For strings, show the full content as-is
            return value
        elif isinstance(value, (dict, list)):
            # For dicts and lists, pretty-print as JSON
            try:
                return json.dumps(value, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(value)
        else:
            # For other types, convert to string
            return str(value)

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        formatted_value = self._format_value(self.field_value)

        with Vertical():
            yield Label(self.panel_label, classes="modal-header")
            yield Label(f'Field: "{self.field_key}"', classes="field-key-label")
            with ScrollableContainer(classes="content-container"):
                yield Static(formatted_value, classes="field-content")
            yield Label("Press [ESC] or [ENTER] to close", classes="close-hint")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
