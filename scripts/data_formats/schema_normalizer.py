"""
Schema normalization utilities for data records.

This module handles the key schema differences between formats:
- JSONL uses 'messages' for conversation data
- Parquet uses 'conversations' for conversation data
- Parquet has different metadata fields (agent, model, episode, etc.)

The standard schema uses 'messages' as the conversation key.
"""

from __future__ import annotations

from typing import Any


def normalize_record(record: dict[str, Any], source_format: str | None = None) -> dict[str, Any]:
    """Normalize record to standard schema.

    Standard schema uses 'messages' as the conversation key and ensures
    all required fields exist with appropriate defaults.

    Args:
        record: The record to normalize.
        source_format: Optional format name for format-specific handling.
                      Can be 'jsonl', 'json', or 'parquet'.

    Returns:
        A normalized copy of the record with standard field names.

    Examples:
        >>> record = {"conversations": [{"role": "user", "content": "Hi"}]}
        >>> normalized = normalize_record(record, "parquet")
        >>> "messages" in normalized
        True
        >>> normalized["conversations"]
        KeyError: 'conversations'
    """
    normalized = record.copy()

    # Handle parquet's "conversations" -> "messages"
    if "conversations" in normalized and "messages" not in normalized:
        normalized["messages"] = normalized.pop("conversations")

    # For parquet files, use trial_name as uuid fallback if uuid is missing
    if source_format == "parquet" and "uuid" not in normalized:
        if "trial_name" in normalized:
            normalized["uuid"] = normalized["trial_name"]

    # Ensure required fields exist with defaults
    normalized.setdefault("uuid", None)
    normalized.setdefault("messages", [])
    normalized.setdefault("tools", [])
    normalized.setdefault("license", None)
    normalized.setdefault("used_in", [])

    return normalized


def denormalize_record(
    record: dict[str, Any], target_format: str
) -> dict[str, Any]:
    """Convert normalized record back to format-specific schema.

    This is useful when writing records to a specific format that
    expects different field names.

    Args:
        record: The normalized record.
        target_format: The target format ('jsonl', 'json', or 'parquet').

    Returns:
        A copy of the record with format-specific field names.

    Examples:
        >>> record = {"messages": [{"role": "user", "content": "Hi"}]}
        >>> parquet_record = denormalize_record(record, "parquet")
        >>> "conversations" in parquet_record
        True
    """
    denormalized = record.copy()

    if target_format == "parquet":
        # Convert messages -> conversations for parquet
        if "messages" in denormalized and "conversations" not in denormalized:
            denormalized["conversations"] = denormalized.pop("messages")

        # Remove fields that don't exist in parquet schema
        # (keeping them won't hurt but this keeps the schema clean)
        # Note: We don't remove these by default to preserve data integrity

    return denormalized


def get_standard_fields() -> list[str]:
    """Return the list of standard schema fields.

    Returns:
        List of standard field names that all normalized records should have.
    """
    return ["uuid", "messages", "tools", "license", "used_in"]


def get_parquet_only_fields() -> list[str]:
    """Return the list of parquet-only metadata fields.

    These fields exist in parquet datasets but not in JSONL datasets.

    Returns:
        List of parquet-specific field names.
    """
    return ["agent", "model", "model_provider", "date", "task", "episode", "run_id", "trial_name"]


def is_normalized(record: dict[str, Any]) -> bool:
    """Check if a record is in normalized form.

    A record is considered normalized if it uses 'messages' (not 'conversations')
    as the conversation key.

    Args:
        record: The record to check.

    Returns:
        True if the record is in normalized form, False otherwise.
    """
    # A record is normalized if it has 'messages' and not 'conversations'
    # (or if it has neither, in which case normalize_record will add defaults)
    has_messages = "messages" in record
    has_conversations = "conversations" in record

    if has_conversations and not has_messages:
        return False

    return True
