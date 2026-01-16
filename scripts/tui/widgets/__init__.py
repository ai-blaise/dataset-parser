"""TUI widgets for the JSON Comparison Viewer."""

from scripts.tui.widgets.json_tree_panel import JsonTreePanel
from scripts.tui.widgets.diff_indicator import (
    calculate_diff,
    get_node_diff_class,
    get_diff_summary,
)
from scripts.tui.widgets.field_detail_modal import FieldDetailModal

__all__ = [
    # JSON tree panel
    "JsonTreePanel",
    # Field detail modal
    "FieldDetailModal",
    # Diff indicator functions
    "calculate_diff",
    "get_node_diff_class",
    "get_diff_summary",
]
