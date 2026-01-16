# Textual TUI Application Plan

## Overview
Build an interactive Terminal User Interface (TUI) using Textual to browse JSONL datasets containing AI conversation data with tool calling.

## Directory Structure
```
scripts/
├── main.py                  # Existing CLI tool (unchanged)
├── parser_finale.py         # NEW: Parser that outputs data without model responses
├── usage.md                 # CLI documentation
└── tui/
    ├── __init__.py
    ├── app.py              # Main application entry point
    ├── data_loader.py      # JSONL loading utilities
    ├── views/
    │   ├── __init__.py
    │   ├── record_list.py  # Record list screen
    │   ├── record_detail.py # Record detail screen
    │   └── field_detail.py # NEW: Field detail modal/screen
    └── widgets/
        ├── __init__.py
        ├── message_viewer.py
        └── tool_viewer.py
```

## Components

### 1. Data Loader (`data_loader.py`)
- Load JSONL files lazily for large datasets
- Provide record summaries and full record access

### 2. Main App (`app.py`)
- Textual App class with screens
- Header with file info
- Footer with keybindings
- Command line argument for file path

### 3. Record List View (`record_list.py`)
- DataTable with columns: IDX, UUID, MSGS, TOOLS, LICENSE, USED_IN, RSN, PREVIEW
- Arrow key navigation
- Enter to view details
- **NEW**: Click on specific column cells to view field details

### 4. Record Detail View (`record_detail.py`)
- TabbedContent with:
  - Messages tab
  - Tools tab
  - Metadata tab
- Back navigation with Escape

### 5. Message Viewer Widget (`message_viewer.py`)
- Display messages with role-based colors
- Show tool_calls and reasoning_content

### 6. Tool Viewer Widget (`tool_viewer.py`)
- List tool names
- Expandable to show parameters/schema

## Keybindings
- `q` - Quit
- `↑/↓` - Navigate
- `Enter` - View details
- `Escape` - Back to list
- `Tab` - Switch tabs

## Running
```bash
uv run python -m scripts.tui.app dataset/interactive_agent.jsonl
```

---

# Enhancement Plan: Field Detail Viewer & Parser Finale

## Phase 1: Field Detail Viewer in TUI

### Goal
Allow users to click/select specific fields in the DataTable (e.g., TOOLS column showing "14") and view detailed information about that field in a modal or dedicated screen.

### Implementation Plan

#### 1.1 Create Field Detail Screen (`scripts/tui/views/field_detail.py`)

A new modal screen that displays detailed field information based on what was clicked.

**Features:**
- Modal overlay that appears on top of the record list
- Different rendering based on field type:
  - **TOOLS**: List all tool names with descriptions
  - **MSGS**: Show message count breakdown by role (system, user, assistant, tool)
  - **UUID**: Show full UUID (currently truncated)
  - **LICENSE**: Show full license text
  - **USED_IN**: Show full list of usage contexts
  - **RSN**: Show reasoning status and count of messages with reasoning_content
  - **PREVIEW**: Show full first user message

**Structure:**
```python
class FieldDetailScreen(ModalScreen):
    """Modal screen to display detailed field information."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self, field_name: str, record: dict, index: int):
        """
        Args:
            field_name: Name of the field (e.g., "tools", "msgs", "uuid")
            record: Full record dictionary
            index: Record index in dataset
        """
        ...

    def compose(self) -> ComposeResult:
        """Render field-specific content in a modal container."""
        ...

    def _render_tools_detail(self) -> Widget:
        """List all tools with names and descriptions."""
        ...

    def _render_msgs_detail(self) -> Widget:
        """Show message breakdown by role."""
        ...

    def _render_uuid_detail(self) -> Widget:
        """Show full UUID."""
        ...

    # ... other field renderers
```

#### 1.2 Modify Record List Screen (`scripts/tui/views/record_list.py`)

**Changes:**
1. Enable cell selection in DataTable (not just row selection)
2. Add handler for cell clicks/selection
3. Map column keys to field names
4. Push FieldDetailScreen modal when cell is clicked

**New Methods:**
```python
def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
    """Handle cell selection to show field details."""
    column_key = event.column_key
    row_key = event.row_key
    # Map column to field, get record, push modal
    ...

def _get_field_for_column(self, column_key: str) -> str:
    """Map DataTable column key to record field name."""
    mapping = {
        "idx": "index",
        "uuid": "uuid",
        "msgs": "messages",
        "tools": "tools",
        "license": "license",
        "used_in": "used_in",
        "rsn": "reasoning",
        "preview": "preview",
    }
    return mapping.get(column_key.value, column_key.value)
```

#### 1.3 Update App (`scripts/tui/app.py`)

**Changes:**
1. Import FieldDetailScreen
2. Add method to show field detail modal

```python
def show_field_detail(self, field_name: str, record: dict, index: int) -> None:
    """Push the field detail modal for the selected field."""
    self.push_screen(FieldDetailScreen(field_name, record, index))
```

### Field Detail Renderings

| Field | Current Display | Detail View Content |
|-------|----------------|---------------------|
| IDX | "0" | Record index with navigation hint |
| UUID | "e4f44d64..." (truncated) | Full UUID with copy hint |
| MSGS | "5" | Breakdown: system(1), user(2), assistant(2), tool(0) |
| TOOLS | "14" | Scrollable list of tool names with descriptions |
| LICENSE | "cc-by-4.0" | Full license name and link if available |
| USED_IN | "['nano..." | Full list of usage contexts |
| RSN | "on" / "-" | Count of messages with reasoning_content |
| PREVIEW | "What is..." | Full first user message content |

---

## Phase 2: Parser Finale (`scripts/parser_finale.py`)

### Goal
Create a parser that outputs JSONL content with emptied assistant responses. Assistant messages are preserved (maintaining conversation structure and `tool_calls`) but their `content` is set to empty string. This is useful for creating training data prompts while preserving the conversation flow.

### What to Include (Keep)
- `uuid` - Record identifier
- `messages` - All messages preserved:
  - `system` messages (unchanged)
  - `user` messages (unchanged)
  - `tool` messages (unchanged)
  - `assistant` messages (kept with empty `content`, `tool_calls` preserved)
- `tools` - Full tool definitions (function schemas)
- `license` - License information
- `used_in` - Usage tracking
- `reasoning` - Reasoning flag (if present)

### What to Empty
- `assistant` message `content` field (set to `""`)

### Output Formats

Support multiple output formats:
1. **JSON** (default): Pretty-printed JSON
2. **JSONL**: One record per line (for processing)
3. **Markdown**: Human-readable formatted output
4. **Text**: Plain text summary

### CLI Interface

```bash
# Basic usage - outputs to stdout
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl

# Specify output format
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --format json
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --format markdown
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --format text

# Output to file
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -o output.json

# Process specific record by index
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --index 5

# Process range of records
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --start 0 --end 10

# Filter records
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --has-tools
```

### Implementation Structure

```python
"""
Parser Finale - Output JSONL content with emptied assistant responses.

This parser processes JSONL records, emptying assistant message content while
preserving the conversation structure, tool_calls, system prompts, user messages,
tools, and metadata.
"""

import argparse
import json
import sys
from typing import Any, Iterator


def process_messages(messages: list[dict]) -> list[dict]:
    """
    Process messages, emptying assistant message content while preserving structure.

    Args:
        messages: List of message dictionaries

    Returns:
        List with assistant messages having empty content (structure and tool_calls preserved)
    """
    result = []
    for msg in messages:
        if msg.get("role") == "assistant":
            # Keep assistant message but empty the content
            processed_msg = {"role": "assistant", "content": ""}
            # Preserve tool_calls as-is if present
            if "tool_calls" in msg:
                processed_msg["tool_calls"] = msg["tool_calls"]
            result.append(processed_msg)
        else:
            # Keep other messages as-is
            result.append(msg)
    return result


def process_record(record: dict) -> dict:
    """
    Process a single record, emptying assistant message content.

    Args:
        record: Full JSONL record

    Returns:
        Record with assistant message content emptied (structure preserved)
    """
    processed = {
        "uuid": record.get("uuid"),
        "messages": process_messages(record.get("messages", [])),
        "tools": record.get("tools", []),
        "license": record.get("license"),
        "used_in": record.get("used_in", []),
    }

    # Include reasoning flag if present
    if "reasoning" in record:
        processed["reasoning"] = record["reasoning"]

    return processed


def format_json(record: dict, pretty: bool = True) -> str:
    """Format record as JSON."""
    if pretty:
        return json.dumps(record, indent=2, ensure_ascii=False)
    return json.dumps(record, ensure_ascii=False)


def format_jsonl(record: dict) -> str:
    """Format record as single JSONL line."""
    return json.dumps(record, ensure_ascii=False)


def format_markdown(record: dict) -> str:
    """Format record as human-readable Markdown."""
    lines = []
    lines.append(f"# Record: {record['uuid']}")
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append(f"- **License:** {record['license']}")
    lines.append(f"- **Used In:** {', '.join(record['used_in'])}")
    if record.get('reasoning'):
        lines.append(f"- **Reasoning:** {record['reasoning']}")
    lines.append("")

    # Messages
    lines.append("## Messages")
    for i, msg in enumerate(record['messages']):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        lines.append(f"### [{i}] {role.upper()}")
        if isinstance(content, dict):
            lines.append("```json")
            lines.append(json.dumps(content, indent=2))
            lines.append("```")
        else:
            lines.append(content if content else "(empty)")
        lines.append("")

    # Tools
    lines.append("## Tools")
    for tool in record['tools']:
        func = tool.get('function', tool)
        name = func.get('name', 'unknown')
        desc = func.get('description', 'No description')
        lines.append(f"### {name}")
        lines.append(f"{desc}")
        lines.append("")

    return "\n".join(lines)


def format_text(record: dict) -> str:
    """Format record as plain text summary."""
    lines = []
    lines.append(f"=== Record: {record['uuid']} ===")
    lines.append(f"License: {record['license']}")
    lines.append(f"Used In: {', '.join(record['used_in'])}")
    lines.append(f"Messages: {len(record['messages'])} (assistant content emptied)")
    lines.append(f"Tools: {len(record['tools'])}")
    lines.append("")

    lines.append("--- Messages ---")
    for i, msg in enumerate(record['messages']):
        role = msg.get('role', 'unknown').upper()
        content = msg.get('content', '')
        if isinstance(content, dict):
            content = json.dumps(content)
        preview = content[:100] + "..." if len(str(content)) > 100 else content
        lines.append(f"[{i}] {role}: {preview}")
    lines.append("")

    lines.append("--- Tools ---")
    for tool in record['tools']:
        func = tool.get('function', tool)
        name = func.get('name', 'unknown')
        lines.append(f"  - {name}")

    return "\n".join(lines)


def load_jsonl(filename: str) -> Iterator[dict]:
    """Lazily load records from JSONL file."""
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    """Main entry point for parser_finale."""
    parser = argparse.ArgumentParser(
        description="Parse JSONL datasets and output content with emptied assistant responses"
    )
    parser.add_argument("filename", help="Path to JSONL file")
    parser.add_argument(
        "-f", "--format",
        choices=["json", "jsonl", "markdown", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "-i", "--index",
        type=int,
        help="Process only record at this index"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start index for range processing"
    )
    parser.add_argument(
        "--end",
        type=int,
        help="End index for range processing"
    )
    parser.add_argument(
        "--has-tools",
        action="store_true",
        help="Only include records with tools"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty print JSON output"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact JSON output (no indentation)"
    )

    args = parser.parse_args()

    # Determine output destination
    output = sys.stdout
    if args.output:
        output = open(args.output, 'w', encoding='utf-8')

    try:
        # Process records
        formatter = {
            "json": lambda r: format_json(r, not args.compact),
            "jsonl": format_jsonl,
            "markdown": format_markdown,
            "text": format_text,
        }[args.format]

        results = []
        for idx, record in enumerate(load_jsonl(args.filename)):
            # Apply index filter
            if args.index is not None and idx != args.index:
                continue

            # Apply range filter
            if idx < args.start:
                continue
            if args.end is not None and idx >= args.end:
                break

            # Apply has-tools filter
            if args.has_tools and not record.get('tools'):
                continue

            processed = process_record(record)

            if args.format == "jsonl":
                print(formatter(processed), file=output)
            else:
                results.append(processed)

        # Output non-JSONL formats
        if args.format != "jsonl" and results:
            if args.format == "json":
                if len(results) == 1:
                    print(formatter(results[0]), file=output)
                else:
                    print(json.dumps(results, indent=2 if not args.compact else None), file=output)
            else:
                for result in results:
                    print(formatter(result), file=output)
                    print("\n" + "="*60 + "\n", file=output)

    finally:
        if args.output:
            output.close()


if __name__ == "__main__":
    main()
```

---

## Implementation Order

### Step 1: Create parser_finale.py
1. Create `/home/archimedes/code/data-gen/scripts/parser_finale.py`
2. Implement core functions: `filter_messages`, `process_record`
3. Implement formatters: `format_json`, `format_jsonl`, `format_markdown`, `format_text`
4. Implement CLI argument parsing
5. Test with sample data

### Step 2: Create Field Detail Screen
1. Create `/home/archimedes/code/data-gen/scripts/tui/views/field_detail.py`
2. Implement FieldDetailScreen as ModalScreen
3. Implement field-specific renderers
4. Add CSS styling for modal

### Step 3: Modify Record List Screen
1. Update DataTable to support cell selection
2. Add `on_data_table_cell_selected` handler
3. Implement column-to-field mapping
4. Connect to FieldDetailScreen

### Step 4: Update App
1. Import FieldDetailScreen
2. Add screen registration if needed
3. Test full flow

---

## Testing Checklist

### Parser Finale Tests
- [ ] JSON output with single record
- [ ] JSON output with multiple records
- [ ] JSONL output format
- [ ] Markdown output format
- [ ] Text output format
- [ ] Index filtering works
- [ ] Range filtering works
- [ ] Has-tools filtering works
- [ ] File output works
- [ ] Stdout output works
- [ ] Assistant messages are preserved with empty content
- [ ] Assistant tool_calls are preserved
- [ ] System, user, tool messages are unchanged
- [ ] Tools array is preserved
- [ ] Metadata fields are preserved

### TUI Field Detail Tests
- [ ] Clicking TOOLS column shows tool list
- [ ] Clicking MSGS column shows message breakdown
- [ ] Clicking UUID column shows full UUID
- [ ] Modal can be dismissed with Escape
- [ ] Modal can be dismissed with Q
- [ ] Content is scrollable for long lists
- [ ] Styling is consistent with app theme
