"""
Record Detail Screen - Shows full details of a single JSONL record with tabs.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

# Try to import custom widgets, with fallback to placeholder implementations
try:
    from scripts.tui.widgets.message_viewer import MessageViewer
    HAS_MESSAGE_VIEWER = True
except ImportError:
    HAS_MESSAGE_VIEWER = False

try:
    from scripts.tui.widgets.tool_viewer import ToolViewer
    HAS_TOOL_VIEWER = True
except ImportError:
    HAS_TOOL_VIEWER = False


class PlaceholderWidget(Static):
    """Placeholder widget when custom widgets are not available."""

    DEFAULT_CSS = """
    PlaceholderWidget {
        padding: 1 2;
        background: $surface;
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self, message: str, data: Any = None) -> None:
        content = f"{message}\n\nData preview:\n{self._format_preview(data)}"
        super().__init__(content)

    def _format_preview(self, data: Any, max_items: int = 5) -> str:
        """Format a preview of the data."""
        if data is None:
            return "(no data)"
        if isinstance(data, list):
            if not data:
                return "(empty list)"
            items = data[:max_items]
            preview_lines = []
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    preview_lines.append(f"  [{i}] {self._dict_preview(item)}")
                else:
                    preview_lines.append(f"  [{i}] {str(item)[:100]}")
            if len(data) > max_items:
                preview_lines.append(f"  ... and {len(data) - max_items} more items")
            return "\n".join(preview_lines)
        return str(data)[:500]

    def _dict_preview(self, d: dict, max_keys: int = 3) -> str:
        """Create a brief preview of a dict."""
        if not d:
            return "{}"
        keys = list(d.keys())[:max_keys]
        parts = [f"{k}: ..." for k in keys]
        if len(d) > max_keys:
            parts.append("...")
        return "{" + ", ".join(parts) + "}"


class MetadataView(VerticalScroll):
    """Widget for displaying record metadata."""

    DEFAULT_CSS = """
    MetadataView {
        padding: 1 2;
        background: $surface;
    }

    MetadataView .metadata-section {
        margin-bottom: 1;
    }

    MetadataView .metadata-label {
        color: $text-muted;
        text-style: bold;
    }

    MetadataView .metadata-value {
        color: $text;
        margin-left: 2;
        margin-bottom: 1;
    }

    MetadataView .metadata-list-item {
        color: $text;
        margin-left: 4;
    }

    MetadataView .reasoning-content {
        color: $warning;
        margin-left: 2;
        padding: 1;
        background: $surface-darken-1;
    }
    """

    def __init__(
        self,
        uuid: str,
        license_val: str,
        used_in: list[str],
        reasoning: str | None,
    ) -> None:
        super().__init__()
        self.uuid = uuid
        self.license_val = license_val
        self.used_in = used_in
        self.reasoning = reasoning

    def compose(self) -> ComposeResult:
        # UUID Section
        yield Static("[b]UUID[/b]", classes="metadata-label")
        yield Static(f"[cyan]{self.uuid}[/cyan]", classes="metadata-value")

        # License Section
        yield Static("[b]License[/b]", classes="metadata-label")
        yield Static(
            f"[green]{self.license_val}[/green]" if self.license_val else "[dim]Not specified[/dim]",
            classes="metadata-value",
        )

        # Used In Section
        yield Static("[b]Used In[/b]", classes="metadata-label")
        if self.used_in:
            for item in self.used_in:
                yield Static(f"[yellow]- {item}[/yellow]", classes="metadata-list-item")
        else:
            yield Static("[dim]Not specified[/dim]", classes="metadata-value")

        # Reasoning Section
        yield Static("[b]Reasoning[/b]", classes="metadata-label")
        if self.reasoning:
            yield Static(
                f"[italic]{self.reasoning}[/italic]",
                classes="reasoning-content",
            )
        else:
            yield Static("[dim]No reasoning provided[/dim]", classes="metadata-value")


class RecordDetailScreen(Screen):
    """Screen showing full details of a single JSONL record with tabs."""

    BINDINGS = [
        Binding("escape", "go_back", "Back to List"),
        Binding("b", "go_back", "Back", show=False),
        Binding("q", "quit", "Quit"),
        Binding("tab", "focus_next", "Next Tab", show=False),
        Binding("shift+tab", "focus_previous", "Previous Tab", show=False),
    ]

    DEFAULT_CSS = """
    RecordDetailScreen {
        background: $background;
    }

    RecordDetailScreen TabbedContent {
        height: 1fr;
    }

    RecordDetailScreen TabPane {
        padding: 0;
    }

    RecordDetailScreen ContentSwitcher {
        height: 1fr;
    }

    RecordDetailScreen #messages-tab,
    RecordDetailScreen #tools-tab,
    RecordDetailScreen #metadata-tab {
        height: 1fr;
        overflow-y: auto;
    }

    RecordDetailScreen Header {
        dock: top;
    }

    RecordDetailScreen Footer {
        dock: bottom;
    }
    """

    def __init__(self, record: dict[str, Any], name: str | None = None) -> None:
        super().__init__(name=name)
        self.record = record
        self.uuid = record.get("uuid", "unknown")
        self.messages = record.get("messages", [])
        self.tools = record.get("tools", [])
        self.license_val = record.get("license", "")
        self.used_in = record.get("used_in", [])
        self.reasoning = record.get("reasoning")

    @property
    def title_text(self) -> str:
        """Get the truncated UUID for the title."""
        if len(self.uuid) > 12:
            return f"Record Detail - {self.uuid[:12]}..."
        return f"Record Detail - {self.uuid}"

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent():
            with TabPane("Messages", id="messages-tab"):
                yield self._create_messages_widget()

            with TabPane("Tools", id="tools-tab"):
                yield self._create_tools_widget()

            with TabPane("Metadata", id="metadata-tab"):
                yield MetadataView(
                    uuid=self.uuid,
                    license_val=self.license_val,
                    used_in=self.used_in,
                    reasoning=self.reasoning,
                )

        yield Footer()

    def _create_messages_widget(self) -> Static | Container:
        """Create the messages viewer widget."""
        if HAS_MESSAGE_VIEWER:
            return MessageViewer(self.messages)
        return PlaceholderWidget(
            "MessageViewer widget not available. "
            "Create scripts/tui/widgets/message_viewer.py to enable.",
            self.messages,
        )

    def _create_tools_widget(self) -> Static | Container:
        """Create the tools viewer widget."""
        if HAS_TOOL_VIEWER:
            return ToolViewer(self.tools)
        return PlaceholderWidget(
            "ToolViewer widget not available. "
            "Create scripts/tui/widgets/tool_viewer.py to enable.",
            self.tools,
        )

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self.title = self.title_text
        self.sub_title = f"{len(self.messages)} messages, {len(self.tools)} tools"

    def action_go_back(self) -> None:
        """Go back to the list screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
