"""
MessageViewer widget for displaying AI chat conversation messages.

This widget displays conversation messages from AI chat data with proper styling
and formatting for different message roles (system, user, assistant, tool).
"""

from __future__ import annotations

import json
from typing import Any, TypedDict

from rich.text import Text
from textual.widgets import Static
from textual.containers import VerticalScroll


class ToolCall(TypedDict, total=False):
    """Type definition for tool call objects."""
    id: str
    type: str
    function: dict[str, Any]


class Message(TypedDict, total=False):
    """Type definition for message objects."""
    role: str
    content: str
    tool_calls: list[ToolCall]
    reasoning_content: str
    tool_call_id: str


# Role color mapping
ROLE_COLORS: dict[str, str] = {
    "system": "yellow",
    "user": "blue",
    "assistant": "green",
    "tool": "magenta",
}


class MessageDisplay(Static):
    """A single message display widget."""

    DEFAULT_CSS = """
    MessageDisplay {
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        message: Message,
        message_index: int = 0,
        **kwargs: Any,
    ) -> None:
        """Initialize the message display.

        Args:
            message: The message dictionary to display.
            message_index: The index of this message in the conversation.
            **kwargs: Additional arguments passed to Static.
        """
        super().__init__(**kwargs)
        self._message = message
        self._message_index = message_index

    def compose_content(self) -> Text:
        """Compose the rich text content for this message."""
        text = Text()

        role = self._message.get("role", "unknown")
        content = self._message.get("content", "")
        tool_calls = self._message.get("tool_calls", [])
        reasoning_content = self._message.get("reasoning_content", "")
        tool_call_id = self._message.get("tool_call_id", "")

        # Get the color for this role
        color = ROLE_COLORS.get(role, "white")

        # Build the role label
        role_label = f"[{role.upper()}]"
        text.append(role_label, style=f"bold {color}")

        # Add tool_call_id for tool messages
        if role == "tool" and tool_call_id:
            text.append(f" (id: {tool_call_id[:20]}...)" if len(tool_call_id) > 20 else f" (id: {tool_call_id})", style="dim")

        text.append(" ")

        # Add reasoning content if present (shown first, dimmed and italic)
        if reasoning_content and reasoning_content.strip():
            text.append("\n")
            text.append("  [reasoning] ", style="dim italic cyan")
            # Wrap reasoning content
            reasoning_lines = reasoning_content.strip().split("\n")
            for i, line in enumerate(reasoning_lines):
                if i > 0:
                    text.append("\n  ")
                text.append(line, style="dim italic")
            text.append("\n")

        # Add main content
        if content and content.strip():
            content_lines = content.strip().split("\n")
            for i, line in enumerate(content_lines):
                if i > 0 or reasoning_content:
                    text.append("\n")
                text.append(line)

        # Add tool calls if present (for assistant messages)
        if tool_calls:
            text.append("\n")
            for tool_call in tool_calls:
                text.append("\n  ")
                text.append("-> ", style="bold yellow")

                # Extract tool call details
                tc_type = tool_call.get("type", "function")
                tc_id = tool_call.get("id", "")
                tc_function = tool_call.get("function", {})
                func_name = tc_function.get("name", "unknown")
                func_args = tc_function.get("arguments", "{}")

                # Format the tool call
                text.append("tool_call: ", style="dim")
                text.append(func_name, style="bold cyan")

                # Parse and format arguments
                try:
                    if isinstance(func_args, str):
                        args_dict = json.loads(func_args)
                    else:
                        args_dict = func_args
                    args_str = json.dumps(args_dict, indent=None, separators=(", ", "="))
                    # Truncate if too long
                    if len(args_str) > 80:
                        args_str = args_str[:77] + "..."
                    text.append(f"({args_str})", style="dim white")
                except (json.JSONDecodeError, TypeError):
                    text.append(f"({func_args})", style="dim white")

                # Show tool call ID if present
                if tc_id:
                    short_id = tc_id[:16] + "..." if len(tc_id) > 16 else tc_id
                    text.append(f" [id: {short_id}]", style="dim italic")

        return text

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.update(self.compose_content())


class MessageViewer(VerticalScroll):
    """A scrollable widget for viewing conversation messages.

    This widget displays a list of messages from an AI chat conversation,
    with proper styling and formatting for different message roles.

    Example usage:
        ```python
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!", "tool_calls": [...]},
        ]
        viewer = MessageViewer(messages=messages)
        ```
    """

    DEFAULT_CSS = """
    MessageViewer {
        height: 100%;
        width: 100%;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }

    MessageViewer > MessageDisplay {
        width: 100%;
    }

    MessageViewer:focus {
        border: solid $accent;
    }
    """

    def __init__(
        self,
        messages: list[Message] | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialize the MessageViewer.

        Args:
            messages: List of message dictionaries to display.
            name: The name of the widget.
            id: The ID of the widget in the DOM.
            classes: Space-separated CSS class names.
            disabled: Whether the widget is disabled.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._messages: list[Message] = messages or []

    def compose(self):
        """Compose the child widgets."""
        for i, message in enumerate(self._messages):
            yield MessageDisplay(message, message_index=i)

    def set_messages(self, messages: list[Message]) -> None:
        """Update the displayed messages.

        Args:
            messages: New list of messages to display.
        """
        self._messages = messages
        self.remove_children()
        for i, message in enumerate(self._messages):
            self.mount(MessageDisplay(message, message_index=i))

    def clear_messages(self) -> None:
        """Clear all messages from the viewer."""
        self._messages = []
        self.remove_children()

    def append_message(self, message: Message) -> None:
        """Append a single message to the viewer.

        Args:
            message: The message to append.
        """
        self._messages.append(message)
        self.mount(MessageDisplay(message, message_index=len(self._messages) - 1))

    @property
    def messages(self) -> list[Message]:
        """Get the current list of messages."""
        return self._messages

    @property
    def message_count(self) -> int:
        """Get the number of messages."""
        return len(self._messages)


# Convenience function to create a simple message viewer app for testing
def create_demo_app():
    """Create a demo Textual app to showcase the MessageViewer."""
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer

    class MessageViewerDemo(App):
        """Demo app for MessageViewer."""

        CSS = """
        Screen {
            layout: vertical;
        }

        MessageViewer {
            height: 1fr;
            margin: 1;
        }
        """

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("r", "refresh", "Refresh"),
        ]

        def compose(self) -> ComposeResult:
            yield Header()

            # Sample messages for demo
            sample_messages: list[Message] = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that can use tools to help users."
                },
                {
                    "role": "user",
                    "content": "Hello, can you help me find information about user 123?"
                },
                {
                    "role": "assistant",
                    "content": "Of course! Let me look up that user information for you.",
                    "reasoning_content": "The user is asking for information about user 123. I should use the get_user_info tool to retrieve this data.",
                    "tool_calls": [
                        {
                            "type": "function",
                            "id": "call_abc123",
                            "function": {
                                "name": "get_user_info",
                                "arguments": '{"user_id": "123"}'
                            }
                        }
                    ]
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_abc123",
                    "content": '{"name": "John Doe", "email": "john@example.com", "status": "active"}'
                },
                {
                    "role": "assistant",
                    "content": "Based on the information I found, user 123 is John Doe with email john@example.com. Their account status is currently active. Is there anything else you'd like to know?"
                },
                {
                    "role": "user",
                    "content": "Thanks! That's all I needed."
                },
            ]

            yield MessageViewer(messages=sample_messages, id="message-viewer")
            yield Footer()

        def action_refresh(self) -> None:
            """Refresh the message viewer."""
            viewer = self.query_one("#message-viewer", MessageViewer)
            viewer.set_messages(viewer.messages)

    return MessageViewerDemo()


if __name__ == "__main__":
    # Run the demo app when executed directly
    app = create_demo_app()
    app.run()
