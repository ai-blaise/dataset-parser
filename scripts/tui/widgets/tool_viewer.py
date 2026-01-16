"""
ToolViewer widget for displaying AI tool/function definitions.

This widget displays tool definitions from AI conversation data using
collapsible sections with Rich markup for styling.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Collapsible, Static


class ToolParameter(Static):
    """Widget to display a single tool parameter."""

    DEFAULT_CSS = """
    ToolParameter {
        padding: 0 0 0 2;
    }
    """

    def __init__(
        self,
        name: str,
        param_type: str,
        required: bool,
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the parameter display.

        Args:
            name: Parameter name.
            param_type: Parameter type (string, number, etc.).
            required: Whether the parameter is required.
            description: Optional parameter description.
            **kwargs: Additional arguments passed to Static.
        """
        super().__init__(**kwargs)
        self._param_name = name
        self._param_type = param_type
        self._required = required
        self._description = description

    def compose(self) -> ComposeResult:
        """Compose the parameter display."""
        required_text = "required" if self._required else "optional"
        required_style = "bold red" if self._required else "dim"

        markup = f"[bold cyan]{self._param_name}[/] ([yellow]{self._param_type}[/], [{required_style}]{required_text}[/])"

        if self._description:
            markup += f" - {self._description}"

        yield Static(f"  [dim]\u2022[/] {markup}")


class ToolDetails(Static):
    """Widget to display tool details including description and parameters."""

    DEFAULT_CSS = """
    ToolDetails {
        padding: 0 0 1 2;
    }

    ToolDetails .tool-description {
        padding: 0 0 1 0;
        color: $text;
    }

    ToolDetails .parameters-header {
        padding: 0 0 0 0;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        description: str | None,
        parameters: dict[str, Any] | None,
        **kwargs: Any,
    ) -> None:
        """Initialize tool details.

        Args:
            description: Tool description.
            parameters: Tool parameters schema.
            **kwargs: Additional arguments passed to Static.
        """
        super().__init__(**kwargs)
        self._description = description
        self._parameters = parameters or {}

    def compose(self) -> ComposeResult:
        """Compose the tool details display."""
        # Description
        if self._description:
            yield Static(
                f"[bold]Description:[/] {self._description}",
                classes="tool-description",
            )
        else:
            yield Static(
                "[bold]Description:[/] [dim]No description available[/]",
                classes="tool-description",
            )

        # Parameters
        properties = self._parameters.get("properties", {})
        required_params = set(self._parameters.get("required", []))

        if properties:
            yield Static("[bold]Parameters:[/]", classes="parameters-header")
            for param_name, param_info in properties.items():
                param_type = self._get_param_type(param_info)
                is_required = param_name in required_params
                param_desc = param_info.get("description")

                yield ToolParameter(
                    name=param_name,
                    param_type=param_type,
                    required=is_required,
                    description=param_desc,
                )
        else:
            yield Static(
                "[bold]Parameters:[/] [dim]None[/]",
                classes="parameters-header",
            )

    def _get_param_type(self, param_info: dict[str, Any]) -> str:
        """Extract the type string from parameter info.

        Args:
            param_info: Parameter schema information.

        Returns:
            Type string representation.
        """
        param_type = param_info.get("type", "unknown")

        # Handle array types
        if param_type == "array":
            items = param_info.get("items", {})
            items_type = items.get("type", "unknown")
            return f"array[{items_type}]"

        # Handle enum types
        if "enum" in param_info:
            enum_values = param_info["enum"]
            if len(enum_values) <= 3:
                return f"enum({', '.join(str(v) for v in enum_values)})"
            return "enum"

        return param_type


class ToolCollapsible(Collapsible):
    """Collapsible widget for a single tool."""

    DEFAULT_CSS = """
    ToolCollapsible {
        padding: 0;
        margin: 0 0 1 0;
        background: $surface;
    }

    ToolCollapsible > CollapsibleTitle {
        padding: 1 2;
        background: $primary-background;
    }

    ToolCollapsible > CollapsibleTitle:hover {
        background: $primary-background-lighten-1;
    }

    ToolCollapsible > Contents {
        padding: 1 2;
    }
    """

    def __init__(self, tool: dict[str, Any], **kwargs: Any) -> None:
        """Initialize the tool collapsible.

        Args:
            tool: Tool definition dictionary.
            **kwargs: Additional arguments passed to Collapsible.
        """
        self._tool = tool
        function_def = tool.get("function", {})
        tool_name = function_def.get("name", "Unknown Tool")

        super().__init__(title=tool_name, collapsed=True, **kwargs)

        self._description = function_def.get("description")
        self._parameters = function_def.get("parameters", {})

    def compose(self) -> ComposeResult:
        """Compose the tool content."""
        yield ToolDetails(
            description=self._description,
            parameters=self._parameters,
        )


class ToolViewer(Widget):
    """Widget to display a list of tool/function definitions.

    This widget takes a list of tool definitions (in OpenAI function calling format)
    and displays them as collapsible items with their descriptions and parameters.

    Example usage:
        ```python
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "authenticate_user",
                    "description": "Authenticate a user by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "The user's ID"},
                            "auth_method": {"type": "string", "description": "Authentication method"},
                        },
                        "required": ["user_id"],
                    },
                },
            }
        ]
        viewer = ToolViewer(tools=tools)
        ```
    """

    DEFAULT_CSS = """
    ToolViewer {
        height: 100%;
        width: 100%;
    }

    ToolViewer > VerticalScroll {
        height: 100%;
        width: 100%;
        padding: 1 2;
    }

    ToolViewer .no-tools {
        padding: 2;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the ToolViewer.

        Args:
            tools: List of tool definitions to display.
            **kwargs: Additional arguments passed to Widget.
        """
        super().__init__(**kwargs)
        self._tools = tools or []

    def compose(self) -> ComposeResult:
        """Compose the tool viewer."""
        with VerticalScroll():
            if not self._tools:
                yield Static(
                    "[dim]No tools available[/]",
                    classes="no-tools",
                )
            else:
                for tool in self._tools:
                    # Handle both direct function format and wrapped format
                    if tool.get("type") == "function" or "function" in tool:
                        yield ToolCollapsible(tool)
                    elif "name" in tool:
                        # Handle case where tool is the function object directly
                        yield ToolCollapsible({"function": tool})

    def update_tools(self, tools: list[dict[str, Any]]) -> None:
        """Update the displayed tools.

        Args:
            tools: New list of tool definitions to display.
        """
        self._tools = tools or []
        self.refresh(recompose=True)

    @property
    def tools(self) -> list[dict[str, Any]]:
        """Get the current list of tools."""
        return self._tools

    @tools.setter
    def tools(self, value: list[dict[str, Any]]) -> None:
        """Set the tools and refresh the display."""
        self.update_tools(value)
