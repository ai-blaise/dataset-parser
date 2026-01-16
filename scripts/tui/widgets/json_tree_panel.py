"""
JSON Tree Panel widget for displaying JSON data in a tree structure.

This module provides a custom Tree widget that renders JSON data with proper
formatting for objects, arrays, and primitive values. It supports synchronized
scrolling and diff highlighting (to be implemented in later phases).
"""

from __future__ import annotations

from typing import Any

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode


class JsonTreePanel(Tree[str]):
    """
    JSON tree widget with support for synchronized scrolling and diff highlighting.

    This widget extends Textual's Tree to display JSON data in a hierarchical
    format with proper rendering for different JSON types:
        - Objects: `{} key_name` (expandable)
        - Arrays: `[] key_name (N items)` (expandable)
        - Strings: `"key": "value"` (leaf)
        - Numbers: `"key": 123` (leaf)
        - Booleans: `"key": true` (leaf)
        - Null: `"key": null` (leaf)

    Attributes:
        sync_enabled: Whether scroll synchronization is enabled.
        diff_mode: Whether diff highlighting is enabled.
    """

    class ScrollChanged(Message):
        """Posted when the scroll position changes.

        This message is emitted when the tree is scrolled, allowing other
        panels to synchronize their scroll position.

        Attributes:
            scroll_y: The vertical scroll position.
            panel_id: The ID of the panel that emitted this message.
        """

        def __init__(self, scroll_y: int, panel_id: str) -> None:
            """Initialize the ScrollChanged message.

            Args:
                scroll_y: The vertical scroll position.
                panel_id: The ID of the panel that emitted this message.
            """
            self.scroll_y = scroll_y
            self.panel_id = panel_id
            super().__init__()

    class NodeToggled(Message):
        """Posted when a node is expanded or collapsed.

        This message is emitted when a tree node's expansion state changes,
        allowing other panels to synchronize their node states.

        Attributes:
            node_path: The path to the node (e.g., "root/messages/[0]").
            expanded: Whether the node is now expanded.
            panel_id: The ID of the panel that emitted this message.
        """

        def __init__(self, node_path: str, expanded: bool, panel_id: str) -> None:
            """Initialize the NodeToggled message.

            Args:
                node_path: The path to the node.
                expanded: Whether the node is now expanded.
                panel_id: The ID of the panel that emitted this message.
            """
            self.node_path = node_path
            self.expanded = expanded
            self.panel_id = panel_id
            super().__init__()

    def __init__(
        self,
        label: str = "root",
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initialize the JSON tree panel.

        Args:
            label: The label for the root node.
            id: The widget ID.
            classes: CSS classes for the widget.
        """
        super().__init__(label, id=id, classes=classes)
        self.sync_enabled: bool = True
        self.diff_mode: bool = False
        self._diff_map: dict[str, str] = {}
        self._node_paths: dict[TreeNode[str], str] = {}

    def set_diff_map(self, diff_map: dict[str, str]) -> None:
        """Set the diff map and apply highlighting to nodes.

        Args:
            diff_map: A dictionary mapping JSON paths to diff types.
        """
        self._diff_map = diff_map
        if self.diff_mode:
            self._apply_diff_highlighting()

    def _apply_diff_highlighting(self) -> None:
        """Apply diff CSS classes to all nodes based on the diff map."""
        self._apply_diff_to_node(self.root)

    def _apply_diff_to_node(self, node: TreeNode[str]) -> None:
        """Recursively apply diff highlighting to a node and its children.

        Args:
            node: The tree node to apply highlighting to.
        """
        # Get the JSON path for this node
        json_path = self._node_paths.get(node, "")

        # Remove existing diff classes
        for css_class in ["diff-unchanged", "diff-changed", "diff-removed", "diff-added"]:
            node.remove_class(css_class)

        # Apply new diff class if in diff mode
        if self.diff_mode and json_path:
            diff_type = self._diff_map.get(json_path, "unchanged")
            node.add_class(f"diff-{diff_type}")

        # Recurse to children
        for child in node.children:
            self._apply_diff_to_node(child)

    def clear_diff_highlighting(self) -> None:
        """Remove all diff highlighting from nodes."""
        self._clear_diff_from_node(self.root)

    def _clear_diff_from_node(self, node: TreeNode[str]) -> None:
        """Recursively remove diff classes from a node and its children.

        Args:
            node: The tree node to clear highlighting from.
        """
        for css_class in ["diff-unchanged", "diff-changed", "diff-removed", "diff-added"]:
            node.remove_class(css_class)

        for child in node.children:
            self._clear_diff_from_node(child)

    def load_json(self, data: dict[str, Any], label: str = "root") -> None:
        """
        Load JSON data into the tree.

        Clears the existing tree and populates it with the provided JSON data.

        Args:
            data: The JSON data to display (typically a dictionary).
            label: The label for the root node.
        """
        self.clear()
        self._node_paths.clear()
        self.root.set_label(label)
        self._add_json_recursive(self.root, data, json_path="")
        self.root.expand()

    def sync_scroll_to(self, scroll_y: int) -> None:
        """Synchronize scroll position from another panel.

        This method is called when another panel scrolls and this panel
        should match the scroll position.

        Args:
            scroll_y: The target vertical scroll position.
        """
        if self.sync_enabled:
            self.scroll_y = scroll_y

    def _on_scroll(self) -> None:
        """Handle scroll events and emit ScrollChanged message."""
        if self.sync_enabled and self.id:
            self.post_message(self.ScrollChanged(self.scroll_y, self.id))

    def sync_node_toggle(self, node_path: str, expanded: bool) -> None:
        """Synchronize node expansion state from another panel.

        This method is called when another panel expands/collapses a node
        and this panel should match the state.

        Args:
            node_path: The path to the node to toggle.
            expanded: Whether the node should be expanded.
        """
        if self.sync_enabled:
            node = self._find_node_by_path(node_path)
            if node:
                if expanded:
                    node.expand()
                else:
                    node.collapse()

    def _find_node_by_path(self, path: str) -> TreeNode[str] | None:
        """Find a tree node by its path.

        Args:
            path: The path to the node (e.g., "root/messages/[0]").

        Returns:
            The TreeNode at the given path, or None if not found.
        """
        if not path:
            return None

        parts = path.split("/")
        current: TreeNode[str] = self.root

        # Skip the first part if it matches the root
        start_idx = 1 if parts and parts[0] == str(current.label) else 0

        for part in parts[start_idx:]:
            found = False
            for child in current.children:
                # Match by label (extract the key part from the label)
                child_label = str(child.label)
                # Handle different label formats
                if part in child_label or child_label.endswith(part):
                    current = child
                    found = True
                    break
            if not found:
                return None

        return current

    def _get_node_path(self, node: TreeNode[str]) -> str:
        """Get the path to a node from the root.

        Args:
            node: The tree node to get the path for.

        Returns:
            The path as a string (e.g., "root/messages/[0]").
        """
        parts: list[str] = []
        current: TreeNode[str] | None = node

        while current is not None:
            parts.append(str(current.label))
            current = current.parent

        parts.reverse()
        return "/".join(parts)

    def _add_json_recursive(
        self,
        node: TreeNode[str],
        data: Any,
        key: str | None = None,
        json_path: str = "",
    ) -> None:
        """
        Recursively add JSON data to the tree.

        Args:
            node: The parent tree node to add children to.
            data: The JSON data to add.
            key: The key name if this is a value in an object.
            json_path: The JSON path to this node (for diff highlighting).
        """
        if isinstance(data, dict):
            self._add_object(node, data, key, json_path)
        elif isinstance(data, list):
            self._add_array(node, data, key, json_path)
        else:
            self._add_primitive(node, data, key, json_path)

    def _add_object(
        self,
        node: TreeNode[str],
        data: dict[str, Any],
        key: str | None = None,
        json_path: str = "",
    ) -> None:
        """
        Add a JSON object to the tree.

        Objects are displayed as expandable nodes with format: `{} key_name`

        Args:
            node: The parent tree node.
            data: The object data.
            key: The key name if this object is a value in a parent object.
            json_path: The JSON path to this node.
        """
        if key is not None:
            label = f"{{}} {key}"
        else:
            label = "{}"

        if node.is_root and key is None:
            # Use root node directly
            child = node
            child.set_label(label)
        else:
            child = node.add(label, allow_expand=True)

        # Store the JSON path for this node
        self._node_paths[child] = json_path

        for obj_key, obj_value in data.items():
            child_path = f"{json_path}.{obj_key}" if json_path else obj_key
            self._add_json_recursive(child, obj_value, obj_key, child_path)

    def _add_array(
        self,
        node: TreeNode[str],
        data: list[Any],
        key: str | None = None,
        json_path: str = "",
    ) -> None:
        """
        Add a JSON array to the tree.

        Arrays are displayed as expandable nodes with format: `[] key_name (N items)`

        Args:
            node: The parent tree node.
            data: The array data.
            key: The key name if this array is a value in a parent object.
            json_path: The JSON path to this node.
        """
        count = len(data)
        items_label = "item" if count == 1 else "items"

        if key is not None:
            label = f"[] {key} ({count} {items_label})"
        else:
            label = f"[] ({count} {items_label})"

        child = node.add(label, allow_expand=True)

        # Store the JSON path for this node
        self._node_paths[child] = json_path

        for idx, item in enumerate(data):
            child_path = f"{json_path}[{idx}]"
            self._add_json_recursive(child, item, f"[{idx}]", child_path)

    def _add_primitive(
        self,
        node: TreeNode[str],
        data: Any,
        key: str | None = None,
        json_path: str = "",
    ) -> None:
        """
        Add a JSON primitive value to the tree.

        Primitives are displayed as leaf nodes with format: `"key": value`

        Args:
            node: The parent tree node.
            data: The primitive value (string, number, boolean, or null).
            key: The key name for this value.
            json_path: The JSON path to this node.
        """
        if data is None:
            value_str = "null"
        elif isinstance(data, bool):
            value_str = "true" if data else "false"
        elif isinstance(data, str):
            # Truncate long strings for display
            if len(data) > 50:
                display_str = data[:47] + "..."
            else:
                display_str = data
            # Escape quotes in the string
            display_str = display_str.replace('"', '\\"')
            value_str = f'"{display_str}"'
        elif isinstance(data, (int, float)):
            value_str = str(data)
        else:
            # Fallback for any other type
            value_str = repr(data)

        if key is not None:
            label = f'"{key}": {value_str}'
        else:
            label = value_str

        leaf = node.add_leaf(label)

        # Store the JSON path for this node
        self._node_paths[leaf] = json_path
