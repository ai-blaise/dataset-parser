"""
Data loader utilities for AI conversation datasets.

This module provides functions for loading and processing data files in various
formats (JSONL, JSON, Parquet) that contain AI conversation records with
messages, tools, and metadata.

Supported Formats:
    - JSONL (.jsonl): One JSON object per line
    - JSON (.json): Array of JSON objects or single object
    - Parquet (.parquet, .pq): Apache Parquet columnar format

Record Structure (after normalization):
    - uuid: Unique identifier string
    - messages: List of message dicts with role, content, tool_calls, reasoning_content
    - tools: List of tool definitions with function.name, function.description, function.parameters
    - license: License string (e.g., "cc-by-4.0")
    - used_in: List of strings indicating usage (e.g., ["nano_v3"])
    - reasoning: Optional string (e.g., "on")

Note: Parquet files may use 'conversations' instead of 'messages' - the loader
normalizes this automatically.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Iterator

from scripts.data_formats import get_loader, normalize_record
from scripts.parser_finale import process_record


# Global cache for loaded records to prevent multiple file reads
_record_cache: dict[str, list[dict[str, Any]]] = {}


def get_cached_records(filename: str) -> list[dict[str, Any]] | None:
    """Get records from cache if available.

    Args:
        filename: Path to the JSONL file.

    Returns:
        Cached records or None if not cached.
    """
    return _record_cache.get(filename)


def set_cached_records(filename: str, records: list[dict[str, Any]]) -> None:
    """Store records in cache.

    Args:
        filename: Path to the JSONL file.
        records: The records to cache.
    """
    _record_cache[filename] = records


def clear_cache(filename: str | None = None) -> None:
    """Clear the record cache.

    Args:
        filename: If provided, only clear cache for this file.
                  If None, clear all cached records.
    """
    if filename:
        _record_cache.pop(filename, None)
    else:
        _record_cache.clear()


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

    Note: For multi-format support, consider using load_records() instead.

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


def load_records(filename: str, normalize: bool = True) -> Iterator[dict[str, Any]]:
    """
    Lazily load records from any supported file format.

    This generator yields one record at a time, making it memory-efficient
    for processing large files. Supports JSONL, JSON, and Parquet formats.

    Args:
        filename: Path to the data file (format detected from extension).
        normalize: Whether to normalize records to standard schema (default True).
                  This converts 'conversations' to 'messages' for Parquet files.

    Yields:
        Each record as a dictionary (normalized if normalize=True).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.

    Examples:
        >>> for record in load_records("data.parquet"):
        ...     print(record["messages"])  # Works even if source has 'conversations'
    """
    loader = get_loader(filename)
    for record in loader.load(filename):
        if normalize:
            yield normalize_record(record, loader.format_name)
        else:
            yield record


def load_all_records(
    filename: str,
    use_cache: bool = True,
    progress_callback: Callable[[int, int | None], None] | None = None,
    max_records: int | None = None,
    normalize: bool = True,
) -> list[dict[str, Any]]:
    """
    Load all records from a data file into memory.

    This function reads the entire file and returns a list of all records.
    Supports JSONL, JSON, and Parquet formats.
    Use load_records() for memory-efficient processing of large files.

    Args:
        filename: Path to the data file (format detected from extension).
        use_cache: Whether to use cached records if available (default True).
        progress_callback: Optional callback(loaded_count, total_count) for progress updates.
                          total_count may be None if unknown.
        max_records: Maximum number of records to load (None = all).
        normalize: Whether to normalize records to standard schema (default True).

    Returns:
        A list of all records as dictionaries (normalized if normalize=True).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.

    Examples:
        >>> records = load_all_records("data.parquet")
        >>> print(f"Loaded {len(records)} records")
    """
    # Check cache first
    if use_cache:
        cached = get_cached_records(filename)
        if cached is not None:
            if max_records is not None:
                return cached[:max_records]
            return cached

    # Load records with optional progress reporting using format-aware loader
    records: list[dict[str, Any]] = []
    for i, record in enumerate(load_records(filename, normalize=normalize)):
        if max_records is not None and i >= max_records:
            break
        records.append(record)
        if progress_callback is not None and i % 1000 == 0:
            progress_callback(i + 1, None)

    # Cache the full load (only if we loaded all records)
    if use_cache and max_records is None:
        set_cached_records(filename, records)

    if progress_callback is not None:
        progress_callback(len(records), len(records))

    return records


def load_record_at_index(
    filename: str, index: int, normalize: bool = True
) -> dict[str, Any]:
    """
    Load a single record at a specific index efficiently.

    Uses cached records if available, otherwise reads from file.
    Supports JSONL, JSON, and Parquet formats.

    Args:
        filename: Path to the data file (format detected from extension).
        index: The index of the record to load.
        normalize: Whether to normalize the record to standard schema (default True).

    Returns:
        The record at the given index (normalized if normalize=True).

    Raises:
        FileNotFoundError: If the file does not exist.
        IndexError: If the index is out of range.
    """
    # Try cache first
    cached = get_cached_records(filename)
    if cached is not None:
        if index < 0 or index >= len(cached):
            raise IndexError(f"Record index {index} out of range (0-{len(cached) - 1})")
        return cached[index]

    # Fall back to streaming read using format-aware loader
    for i, record in enumerate(load_records(filename, normalize=normalize)):
        if i == index:
            return record

    raise IndexError(f"Record index {index} out of range")


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


def load_record_pair(
    filename: str,
    index: int,
    cached_records: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load a single record and return both original and processed versions.

    This function loads the original record from the JSONL file and processes
    it through parser_finale to create the comparison pair.

    Args:
        filename: Path to the JSONL file.
        index: The index of the record to load.
        cached_records: Optional pre-loaded records list to use instead of file.

    Returns:
        A tuple of (original_record, processed_record) where:
            - original_record: The raw record from the JSONL file
            - processed_record: The record after parser_finale processing
              (assistant content emptied, reasoning_content removed)

    Raises:
        FileNotFoundError: If the file does not exist.
        IndexError: If the index is out of range.

    Examples:
        >>> original, processed = load_record_pair("data.jsonl", 0)
        >>> print(original["messages"][0]["content"])  # Full content
        >>> print(processed["messages"][0]["content"])  # Empty if assistant
    """
    # Use provided cached records, global cache, or load from file
    if cached_records is not None:
        if index < 0 or index >= len(cached_records):
            raise IndexError(f"Record index {index} out of range (0-{len(cached_records) - 1})")
        original = cached_records[index]
    else:
        original = load_record_at_index(filename, index)

    processed = process_record(original)
    return (original, processed)


def get_record_diff(original: dict[str, Any], processed: dict[str, Any]) -> dict[str, str]:
    """
    Calculate differences between original and processed records.

    Compares the two JSON structures and returns a mapping of JSON paths
    to their diff status.

    Args:
        original: The original record dictionary.
        processed: The processed record dictionary.

    Returns:
        A dictionary mapping JSON paths to diff types:
            - "unchanged": Values match exactly
            - "changed": Value differs between original and processed
            - "removed": Key exists in original but not in processed
            - "added": Key exists in processed but not in original

    Examples:
        >>> diff = get_record_diff(original, processed)
        >>> print(diff.get("messages[1].content"))  # "changed" for assistant
    """
    # Stub implementation - will be fully implemented in diff_indicator.py
    return {}


def export_records(
    records: list[dict[str, Any]],
    output_dir: str,
    source_filename: str,
    format: str = "json",
) -> str:
    """
    Export processed records to an output directory.

    Creates the output directory if it doesn't exist and writes records
    to a file named {original_stem}_parsed.{format}.

    Args:
        records: List of record dictionaries to export.
        output_dir: Directory path for output files.
        source_filename: Original source filename (used for output naming).
        format: Output format ('json' or 'jsonl'). Defaults to 'json'.

    Returns:
        The path to the created output file.

    Raises:
        ValueError: If format is not supported.
        OSError: If the output directory cannot be created or file cannot be written.

    Examples:
        >>> path = export_records(records, "parsed_datasets", "train.jsonl")
        >>> print(f"Exported to {path}")  # "parsed_datasets/train_parsed.json"
    """
    if format not in ("json", "jsonl"):
        raise ValueError(f"Unsupported export format: {format}. Use 'json' or 'jsonl'.")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Construct output filename
    source_path = Path(source_filename)
    output_filename = f"{source_path.stem}_parsed.{format}"
    output_path = Path(output_dir) / output_filename

    # Write records to file
    with open(output_path, "w", encoding="utf-8") as f:
        if format == "json":
            json.dump(records, f, indent=2, ensure_ascii=False)
        else:  # jsonl
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return str(output_path)
