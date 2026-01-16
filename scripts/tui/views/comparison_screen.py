"""
Comparison Screen for side-by-side JSON comparison.

Displays original JSONL records alongside parser_finale processed output
in a split-screen view with synchronized navigation.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from scripts.tui.data_loader import load_record_pair
from scripts.tui.widgets.diff_indicator import calculate_diff
from scripts.tui.widgets.json_tree_panel import JsonTreePanel


class ComparisonScreen(Screen):
    """Side-by-side JSON comparison view.

    This screen displays the original JSONL record on the left and the
    parser_finale processed output on the right, allowing comparison
    of the transformation.
    """

    CSS = """
    ComparisonScreen {
        layout: vertical;
    }

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

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }

    /* Diff highlighting classes (to be used by diff functionality) */
    .diff-added {
        background: $success 20%;
    }

    .diff-removed {
        background: $error 20%;
    }

    .diff-changed {
        background: $warning 20%;
    }
    """

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("b", "go_back", "Back", show=False),
        Binding("q", "quit", "Quit"),
        Binding("left", "focus_left", "Left Panel", show=False),
        Binding("right", "focus_right", "Right Panel", show=False),
        Binding("tab", "switch_panel", "Switch Panel"),
        Binding("s", "toggle_sync", "Sync Scroll"),
        Binding("d", "toggle_diff", "Show Diff"),
        Binding("space", "toggle_node", "Expand/Collapse", show=False),
        Binding("e", "expand_all", "Expand All"),
        Binding("c", "collapse_all", "Collapse All"),
    ]

    def __init__(
        self,
        filename: str,
        record_index: int,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the ComparisonScreen.

        Args:
            filename: Path to the JSONL file.
            record_index: Index of the record to display.
            name: Optional name for the screen.
            id: Optional ID for the screen.
            classes: Optional CSS classes for the screen.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._filename = filename
        self._record_index = record_index
        self._original: dict[str, Any] = {}
        self._processed: dict[str, Any] = {}
        self._sync_enabled: bool = True
        self._diff_enabled: bool = False
        self._active_panel: str = "left"

    def compose(self) -> ComposeResult:
        """Compose the screen layout with side-by-side panels."""
        yield Header()
        with Horizontal(id="comparison-container"):
            with Vertical(id="left-panel"):
                yield Static("ORIGINAL JSONL", classes="panel-header")
                yield JsonTreePanel(label="original", id="left-tree")
            with Vertical(id="right-panel"):
                yield Static("PARSER_FINALE OUTPUT", classes="panel-header")
                yield JsonTreePanel(label="processed", id="right-tree")
        yield Footer()

    def on_mount(self) -> None:
        """Load data when screen is mounted."""
        self._load_comparison_data()

    def _load_comparison_data(self) -> None:
        """Load the original and processed records and display them."""
        try:
            self._original, self._processed = load_record_pair(
                self._filename, self._record_index
            )
        except (FileNotFoundError, IndexError) as e:
            # Show error in both panels
            self._original = {"error": str(e)}
            self._processed = {"error": str(e)}

        # Get UUID for title
        uuid = self._original.get("uuid", "Unknown")
        self.title = f"Record {self._record_index}: {uuid}"

        # Load data into tree panels
        left_tree = self.query_one("#left-tree", JsonTreePanel)
        right_tree = self.query_one("#right-tree", JsonTreePanel)

        left_tree.load_json(self._original, label=f"Record {self._record_index}")
        right_tree.load_json(self._processed, label=f"Record {self._record_index}")

        # Focus the left panel by default
        left_tree.focus()

    def action_go_back(self) -> None:
        """Return to the record list screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_focus_left(self) -> None:
        """Focus the left panel."""
        self._active_panel = "left"
        self.query_one("#left-tree", JsonTreePanel).focus()

    def action_focus_right(self) -> None:
        """Focus the right panel."""
        self._active_panel = "right"
        self.query_one("#right-tree", JsonTreePanel).focus()

    def action_switch_panel(self) -> None:
        """Switch focus between left and right panels."""
        if self._active_panel == "left":
            self.action_focus_right()
        else:
            self.action_focus_left()

    def action_toggle_sync(self) -> None:
        """Toggle synchronized scrolling between panels."""
        self._sync_enabled = not self._sync_enabled
        left_tree = self.query_one("#left-tree", JsonTreePanel)
        right_tree = self.query_one("#right-tree", JsonTreePanel)
        left_tree.sync_enabled = self._sync_enabled
        right_tree.sync_enabled = self._sync_enabled

        status = "enabled" if self._sync_enabled else "disabled"
        self.notify(f"Sync scroll {status}")

    def action_toggle_diff(self) -> None:
        """Toggle diff highlighting."""
        self._diff_enabled = not self._diff_enabled
        left_tree = self.query_one("#left-tree", JsonTreePanel)
        right_tree = self.query_one("#right-tree", JsonTreePanel)

        if self._diff_enabled:
            # Calculate the diff between original and processed
            diff_map = calculate_diff(self._original, self._processed)

            # Apply diff highlighting to both trees
            left_tree.set_diff_map(diff_map)
            right_tree.set_diff_map(diff_map)

            # Enable diff mode on both trees
            left_tree.diff_mode = True
            right_tree.diff_mode = True

            # Apply the highlighting
            left_tree._apply_diff_highlighting()
            right_tree._apply_diff_highlighting()
        else:
            # Disable diff mode and clear highlighting
            left_tree.diff_mode = False
            right_tree.diff_mode = False
            left_tree.clear_diff_highlighting()
            right_tree.clear_diff_highlighting()

        status = "enabled" if self._diff_enabled else "disabled"
        self.notify(f"Diff highlighting {status}")

    def action_toggle_node(self) -> None:
        """Toggle expand/collapse on the current node."""
        # Get the currently focused tree
        if self._active_panel == "left":
            tree = self.query_one("#left-tree", JsonTreePanel)
        else:
            tree = self.query_one("#right-tree", JsonTreePanel)

        # Toggle the current node
        if tree.cursor_node:
            tree.cursor_node.toggle()

    def action_expand_all(self) -> None:
        """Expand all nodes in both trees."""
        left_tree = self.query_one("#left-tree", JsonTreePanel)
        right_tree = self.query_one("#right-tree", JsonTreePanel)

        self._expand_all_nodes(left_tree.root)
        self._expand_all_nodes(right_tree.root)

        self.notify("Expanded all nodes")

    def action_collapse_all(self) -> None:
        """Collapse all nodes in both trees."""
        left_tree = self.query_one("#left-tree", JsonTreePanel)
        right_tree = self.query_one("#right-tree", JsonTreePanel)

        self._collapse_all_nodes(left_tree.root)
        self._collapse_all_nodes(right_tree.root)

        self.notify("Collapsed all nodes")

    def _expand_all_nodes(self, node: Any) -> None:
        """Recursively expand all nodes starting from the given node."""
        node.expand()
        for child in node.children:
            self._expand_all_nodes(child)

    def _collapse_all_nodes(self, node: Any) -> None:
        """Recursively collapse all nodes starting from the given node."""
        for child in node.children:
            self._collapse_all_nodes(child)
        if not node.is_root:
            node.collapse()

    def on_json_tree_panel_scroll_changed(
        self, message: JsonTreePanel.ScrollChanged
    ) -> None:
        """Handle scroll sync between panels.

        When one panel scrolls, synchronize the other panel to the same
        scroll position if sync is enabled.

        Args:
            message: The ScrollChanged message from a JsonTreePanel.
        """
        if not self._sync_enabled:
            return

        left_tree = self.query_one("#left-tree", JsonTreePanel)
        right_tree = self.query_one("#right-tree", JsonTreePanel)

        # Sync the other panel
        if message.panel_id == "left-tree":
            right_tree.sync_scroll_to(message.scroll_y)
        elif message.panel_id == "right-tree":
            left_tree.sync_scroll_to(message.scroll_y)

    def on_json_tree_panel_node_toggled(
        self, message: JsonTreePanel.NodeToggled
    ) -> None:
        """Handle node toggle sync between panels.

        When one panel expands/collapses a node, synchronize the other
        panel to the same state if sync is enabled.

        Args:
            message: The NodeToggled message from a JsonTreePanel.
        """
        if not self._sync_enabled:
            return

        left_tree = self.query_one("#left-tree", JsonTreePanel)
        right_tree = self.query_one("#right-tree", JsonTreePanel)

        # Sync the other panel
        if message.panel_id == "left-tree":
            right_tree.sync_node_toggle(message.node_path, message.expanded)
        elif message.panel_id == "right-tree":
            left_tree.sync_node_toggle(message.node_path, message.expanded)

    @property
    def original_record(self) -> dict[str, Any]:
        """Get the original record."""
        return self._original

    @property
    def processed_record(self) -> dict[str, Any]:
        """Get the processed record."""
        return self._processed

    @property
    def sync_enabled(self) -> bool:
        """Check if sync scrolling is enabled."""
        return self._sync_enabled

    @property
    def diff_enabled(self) -> bool:
        """Check if diff highlighting is enabled."""
        return self._diff_enabled
