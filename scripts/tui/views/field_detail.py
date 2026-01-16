"""
Field Detail Modal Screen for JSONL Dataset Explorer.

Displays detailed information about a specific field when a cell is clicked.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Label


class FieldDetailScreen(ModalScreen[None]):
    """Modal screen to display detailed field information."""

    CSS = """
    FieldDetailScreen {
        align: center middle;
    }

    #modal-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #modal-header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        text-align: center;
        padding: 1;
        text-style: bold;
    }

    #modal-content {
        height: 1fr;
        padding: 1;
    }

    .field-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }

    .field-value {
        color: $text;
        margin-bottom: 1;
    }

    .tool-item {
        padding: 1;
        margin-bottom: 1;
        background: $surface-darken-1;
        border: solid $primary-darken-2;
    }

    .tool-name {
        text-style: bold;
        color: $accent;
    }

    .tool-desc {
        color: $text-muted;
        margin-top: 1;
    }

    .msg-role {
        text-style: bold;
        padding: 0 1;
    }

    .msg-role-system {
        color: $warning;
    }

    .msg-role-user {
        color: $success;
    }

    .msg-role-assistant {
        color: $primary;
    }

    .msg-role-tool {
        color: $secondary;
    }

    .uuid-full {
        color: $accent;
        background: $surface-darken-1;
        padding: 1;
    }

    .preview-full {
        background: $surface-darken-1;
        padding: 1;
        border: solid $primary-darken-2;
    }

    #hint {
        dock: bottom;
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(
        self,
        field_name: str,
        record: dict[str, Any],
        index: int,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initialize the field detail modal.

        Args:
            field_name: Name of the field to display (e.g., "tools", "msgs")
            record: Full record dictionary
            index: Record index in dataset
            name: Optional name for the screen
            id: Optional ID for the screen
            classes: Optional CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.field_name = field_name
        self.record = record
        self.record_index = index

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Container(id="modal-container"):
            yield Static(self._get_header_text(), id="modal-header")
            with VerticalScroll(id="modal-content"):
                yield from self._render_field_content()
            yield Static("Press [ESC] or [Q] to close", id="hint")

    def _get_header_text(self) -> str:
        """Get the header text based on field name."""
        headers = {
            "index": f"Record Index: {self.record_index}",
            "uuid": "Full UUID",
            "messages": "Message Breakdown",
            "tools": "Tools List",
            "license": "License Information",
            "used_in": "Usage Contexts",
            "reasoning": "Reasoning Information",
            "preview": "First User Message",
        }
        return headers.get(self.field_name, f"Field: {self.field_name}")

    def _render_field_content(self) -> list[Static]:
        """Render content based on field type."""
        renderers = {
            "index": self._render_index_detail,
            "uuid": self._render_uuid_detail,
            "messages": self._render_msgs_detail,
            "tools": self._render_tools_detail,
            "license": self._render_license_detail,
            "used_in": self._render_used_in_detail,
            "reasoning": self._render_reasoning_detail,
            "preview": self._render_preview_detail,
        }
        renderer = renderers.get(self.field_name, self._render_default)
        return renderer()

    def _render_index_detail(self) -> list[Static]:
        """Render index information."""
        return [
            Static(f"[b]Record Index:[/b] {self.record_index}", classes="field-value"),
            Static(f"[b]UUID:[/b] {self.record.get('uuid', 'N/A')}", classes="field-value"),
            Static("", classes="field-value"),
            Static("[dim]Use arrow keys in the list to navigate between records.[/dim]", classes="field-value"),
        ]

    def _render_uuid_detail(self) -> list[Static]:
        """Render full UUID."""
        uuid = self.record.get("uuid", "N/A")
        return [
            Static("[b]Full UUID:[/b]", classes="field-title"),
            Static(uuid, classes="uuid-full"),
            Static("", classes="field-value"),
            Static(f"[dim]Length: {len(uuid)} characters[/dim]", classes="field-value"),
        ]

    def _render_msgs_detail(self) -> list[Static]:
        """Render message breakdown by role."""
        messages = self.record.get("messages", [])
        role_counts: Counter[str] = Counter()
        reasoning_count = 0

        for msg in messages:
            role = msg.get("role", "unknown")
            role_counts[role] += 1
            if msg.get("reasoning_content"):
                reasoning_count += 1

        widgets: list[Static] = [
            Static(f"[b]Total Messages:[/b] {len(messages)}", classes="field-title"),
            Static("", classes="field-value"),
            Static("[b]Breakdown by Role:[/b]", classes="field-title"),
        ]

        role_colors = {
            "system": "warning",
            "user": "success",
            "assistant": "primary",
            "tool": "secondary",
        }

        for role in ["system", "user", "assistant", "tool"]:
            count = role_counts.get(role, 0)
            color = role_colors.get(role, "text")
            widgets.append(
                Static(f"  [{color}]{role.upper()}:[/{color}] {count}", classes="field-value")
            )

        # Other roles if any
        for role, count in role_counts.items():
            if role not in ["system", "user", "assistant", "tool"]:
                widgets.append(Static(f"  {role.upper()}: {count}", classes="field-value"))

        widgets.append(Static("", classes="field-value"))
        widgets.append(
            Static(f"[b]Messages with reasoning_content:[/b] {reasoning_count}", classes="field-value")
        )

        return widgets

    def _render_tools_detail(self) -> list[Static]:
        """Render list of all tools with descriptions."""
        tools = self.record.get("tools", [])
        widgets: list[Static] = [
            Static(f"[b]Total Tools:[/b] {len(tools)}", classes="field-title"),
            Static("", classes="field-value"),
        ]

        if not tools:
            widgets.append(Static("[dim]No tools defined for this record.[/dim]", classes="field-value"))
            return widgets

        for i, tool in enumerate(tools):
            func = tool.get("function", tool)
            name = func.get("name", "unknown")
            desc = func.get("description", "No description available")

            # Truncate description if too long
            if len(desc) > 200:
                desc = desc[:197] + "..."

            widgets.append(Static(f"[b cyan]{i + 1}. {name}[/b cyan]", classes="tool-name"))
            widgets.append(Static(f"   [dim]{desc}[/dim]", classes="tool-desc"))
            widgets.append(Static("", classes="field-value"))

        return widgets

    def _render_license_detail(self) -> list[Static]:
        """Render license information."""
        license_text = self.record.get("license", "N/A")

        license_info = {
            "cc-by-4.0": "Creative Commons Attribution 4.0 International",
            "cc-by-sa-4.0": "Creative Commons Attribution-ShareAlike 4.0 International",
            "cc-by-nc-4.0": "Creative Commons Attribution-NonCommercial 4.0 International",
            "mit": "MIT License",
            "apache-2.0": "Apache License 2.0",
        }

        full_name = license_info.get(license_text.lower(), "Unknown License")

        return [
            Static("[b]License ID:[/b]", classes="field-title"),
            Static(f"  {license_text}", classes="field-value"),
            Static("", classes="field-value"),
            Static("[b]Full Name:[/b]", classes="field-title"),
            Static(f"  {full_name}", classes="field-value"),
        ]

    def _render_used_in_detail(self) -> list[Static]:
        """Render usage contexts."""
        used_in = self.record.get("used_in", [])
        widgets: list[Static] = [
            Static(f"[b]Usage Contexts:[/b] {len(used_in)}", classes="field-title"),
            Static("", classes="field-value"),
        ]

        if not used_in:
            widgets.append(Static("[dim]No usage contexts specified.[/dim]", classes="field-value"))
            return widgets

        for item in used_in:
            widgets.append(Static(f"  - {item}", classes="field-value"))

        return widgets

    def _render_reasoning_detail(self) -> list[Static]:
        """Render reasoning information."""
        reasoning = self.record.get("reasoning")
        messages = self.record.get("messages", [])

        # Count messages with reasoning_content
        reasoning_count = sum(1 for msg in messages if msg.get("reasoning_content"))

        widgets: list[Static] = [
            Static("[b]Reasoning Mode:[/b]", classes="field-title"),
            Static(f"  {reasoning if reasoning else 'Not specified'}", classes="field-value"),
            Static("", classes="field-value"),
            Static("[b]Messages with reasoning_content:[/b]", classes="field-title"),
            Static(f"  {reasoning_count} of {len(messages)} messages", classes="field-value"),
        ]

        if reasoning_count > 0:
            widgets.append(Static("", classes="field-value"))
            widgets.append(Static("[b]Roles with reasoning:[/b]", classes="field-title"))
            roles_with_reasoning: Counter[str] = Counter()
            for msg in messages:
                if msg.get("reasoning_content"):
                    roles_with_reasoning[msg.get("role", "unknown")] += 1
            for role, count in roles_with_reasoning.items():
                widgets.append(Static(f"  - {role}: {count}", classes="field-value"))

        return widgets

    def _render_preview_detail(self) -> list[Static]:
        """Render full first user message."""
        messages = self.record.get("messages", [])

        # Find first user message
        first_user_msg = None
        for msg in messages:
            if msg.get("role") == "user":
                first_user_msg = msg
                break

        widgets: list[Static] = [
            Static("[b]First User Message:[/b]", classes="field-title"),
            Static("", classes="field-value"),
        ]

        if first_user_msg is None:
            widgets.append(Static("[dim]No user messages in this record.[/dim]", classes="field-value"))
            return widgets

        content = first_user_msg.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content, indent=2)

        if not content:
            widgets.append(Static("[dim](Empty message)[/dim]", classes="field-value"))
        else:
            widgets.append(Static(content, classes="preview-full"))

        return widgets

    def _render_default(self) -> list[Static]:
        """Render default field view."""
        value = self.record.get(self.field_name, "N/A")
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)
        return [
            Static(f"[b]Field:[/b] {self.field_name}", classes="field-title"),
            Static(f"[b]Value:[/b]", classes="field-title"),
            Static(str(value), classes="field-value"),
        ]

    def action_dismiss(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)
