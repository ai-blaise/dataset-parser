"""
Parser Finale - Output JSONL content with emptied assistant responses.

This parser processes JSONL records, emptying assistant message content while
preserving the conversation structure, tool_calls, system prompts, user messages,
tools, and metadata.

Usage:
    uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl
    uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --format markdown
    uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -i 5 -o output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterator


def process_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def process_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Process a single record, emptying assistant message content.

    Args:
        record: Full JSONL record

    Returns:
        Record with assistant message content emptied (structure preserved)
    """
    processed: dict[str, Any] = {
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


def format_json(record: dict[str, Any], pretty: bool = True) -> str:
    """Format record as JSON."""
    if pretty:
        return json.dumps(record, indent=2, ensure_ascii=False)
    return json.dumps(record, ensure_ascii=False)


def format_jsonl(record: dict[str, Any]) -> str:
    """Format record as single JSONL line."""
    return json.dumps(record, ensure_ascii=False)


def format_markdown(record: dict[str, Any]) -> str:
    """Format record as human-readable Markdown."""
    lines: list[str] = []
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


def format_text(record: dict[str, Any]) -> str:
    """Format record as plain text summary."""
    lines: list[str] = []
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
        content_str = str(content) if content else ""
        preview = content_str[:100] + "..." if len(content_str) > 100 else content_str
        lines.append(f"[{i}] {role}: {preview}")
    lines.append("")

    lines.append("--- Tools ---")
    for tool in record['tools']:
        func = tool.get('function', tool)
        name = func.get('name', 'unknown')
        lines.append(f"  - {name}")

    return "\n".join(lines)


def load_jsonl(filename: str) -> Iterator[dict[str, Any]]:
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
        "--compact",
        action="store_true",
        help="Compact JSON output (no indentation)"
    )

    args = parser.parse_args()

    # Verify file exists
    try:
        with open(args.filename, 'r') as f:
            pass
    except FileNotFoundError:
        print(f"Error: File not found: {args.filename}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied: {args.filename}", file=sys.stderr)
        sys.exit(1)

    # Determine output destination
    output_file = None
    output = sys.stdout
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        output = output_file

    try:
        # Select formatter
        formatters = {
            "json": lambda r: format_json(r, not args.compact),
            "jsonl": format_jsonl,
            "markdown": format_markdown,
            "text": format_text,
        }
        formatter = formatters[args.format]

        results: list[dict[str, Any]] = []
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
                    indent = 2 if not args.compact else None
                    print(json.dumps(results, indent=indent, ensure_ascii=False), file=output)
            else:
                for i, result in enumerate(results):
                    print(formatter(result), file=output)
                    if i < len(results) - 1:
                        print("\n" + "=" * 60 + "\n", file=output)

    finally:
        if output_file:
            output_file.close()


if __name__ == "__main__":
    main()
