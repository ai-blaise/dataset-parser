"""TUI widgets for the JSON Comparison Viewer."""

from scripts.tui.widgets.json_tree_panel import JsonTreePanel
from scripts.tui.widgets.diff_indicator import (
    calculate_diff,
    get_node_diff_class,
    get_diff_summary,
)

__all__ = [
    # JSON tree panel
    "JsonTreePanel",
    # Diff indicator functions
    "calculate_diff",
    "get_node_diff_class",
    "get_diff_summary",
]
