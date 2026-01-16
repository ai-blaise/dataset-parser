"""
Data loader utilities for JSONL files containing AI conversation data.

This module provides functions for loading and processing JSONL files that contain
AI conversation records with messages, tools, and metadata.

Record Structure:
    - uuid: Unique identifier string
    - messages: List of message dicts with role, content, tool_calls, reasoning_content
    - tools: List of tool definitions with function.name, function.description, function.parameters
    - license: License string (e.g., "cc-by-4.0")
    - used_in: List of strings indicating usage (e.g., ["nano_v3"])
    - reasoning: Optional string (e.g., "on")
"""

from __future__ import annotations

import json
from typing import Any, Iterator


def truncate(text: str, max_len: int) -> str:
    """
    Truncate text to a maximum length, adding ellipsis if truncated.

    Args:
        text: The text to truncate.
        max_len: Maximum length of the output string (including ellipsis).

    Returns:
        The truncated string with ellipsis if it exceeded max_len,
        otherwise the original string.

    Examples:
        >>> truncate("Hello, World!", 10)
        'Hello, ...'
        >>> truncate("Short", 10)
        'Short'
    """
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def load_jsonl(filename: str) -> Iterator[dict[str, Any]]:
    """
    Lazily load records from a JSONL file.

    This generator yields one record at a time, making it memory-efficient
    for processing large files.

    Args:
        filename: Path to the JSONL file.

    Yields:
        Each record as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If a line contains invalid JSON.

    Examples:
        >>> for record in load_jsonl("data.jsonl"):
        ...     print(record["uuid"])
    """
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_all_records(filename: str) -> list[dict[str, Any]]:
    """
    Load all records from a JSONL file into memory.

    This function reads the entire file and returns a list of all records.
    Use load_jsonl() for memory-efficient processing of large files.

    Args:
        filename: Path to the JSONL file.

    Returns:
        A list of all records as dictionaries.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If a line contains invalid JSON.

    Examples:
        >>> records = load_all_records("data.jsonl")
        >>> print(f"Loaded {len(records)} records")
    """
    return list(load_jsonl(filename))


def get_record_summary(record: dict[str, Any], idx: int) -> dict[str, Any]:
    """
    Generate a summary of a conversation record.

    Extracts key metadata from a record for display purposes, including
    a preview of the first user message.

    Args:
        record: A conversation record dictionary.
        idx: The index of the record in the dataset.

    Returns:
        A dictionary containing:
            - index: The record index
            - uuid: Truncated UUID (first 8 characters with ellipsis)
            - msg_count: Number of messages in the conversation
            - tool_count: Number of tools available
            - license: The license string
            - used_in: List of usage contexts
            - reasoning: Reasoning mode if present, None otherwise
            - preview: First user message truncated to 40 characters

    Examples:
        >>> summary = get_record_summary(record, 0)
        >>> print(f"{summary['index']}: {summary['preview']}")
    """
    messages = record.get("messages", [])
    tools = record.get("tools", [])

    # Find the first user message for preview
    preview = ""
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                preview = truncate(content.strip(), 40)
                break

    # Truncate UUID to 8 characters (showing first 8 chars + ellipsis)
    uuid_full = record.get("uuid", "")
    uuid_truncated = truncate(uuid_full, 8)

    return {
        "index": idx,
        "uuid": uuid_truncated,
        "msg_count": len(messages),
        "tool_count": len(tools),
        "license": record.get("license", ""),
        "used_in": record.get("used_in", []),
        "reasoning": record.get("reasoning"),
        "preview": preview,
    }
