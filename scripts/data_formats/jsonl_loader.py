"""
JSONL format data loader.

This module provides the JSONLLoader class for loading JSONL (JSON Lines) files
where each line is a valid JSON object.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterator

from scripts.data_formats.base import DataLoader


class JSONLLoader(DataLoader):
    """Data loader for JSONL (JSON Lines) format.

    JSONL files contain one JSON object per line, making them efficient
    for streaming large datasets line by line.

    Attributes:
        format_name: Returns 'jsonl'.
        supported_extensions: Returns ['.jsonl'].
    """

    @property
    def format_name(self) -> str:
        """Return the format name."""
        return "jsonl"

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".jsonl"]

    def load(self, filename: str) -> Iterator[dict[str, Any]]:
        """Lazily load records from a JSONL file.

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
            >>> loader = JSONLLoader()
            >>> for record in loader.load("data.jsonl"):
            ...     print(record["uuid"])
        """
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def load_all(
        self,
        filename: str,
        max_records: int | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Load all records from a JSONL file into memory.

        Args:
            filename: Path to the JSONL file.
            max_records: Maximum number of records to load (None = all).
            progress_callback: Optional callback(loaded_count, total_count) for
                              progress updates. total_count may be None if unknown.

        Returns:
            A list of all records as dictionaries.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If a line contains invalid JSON.

        Examples:
            >>> loader = JSONLLoader()
            >>> records = loader.load_all("data.jsonl")
            >>> print(f"Loaded {len(records)} records")
        """
        records: list[dict[str, Any]] = []

        for i, record in enumerate(self.load(filename)):
            if max_records is not None and i >= max_records:
                break
            records.append(record)
            if progress_callback is not None and i % 1000 == 0:
                progress_callback(i + 1, None)

        if progress_callback is not None:
            progress_callback(len(records), len(records))

        return records

    def get_record_count(self, filename: str) -> int:
        """Get total number of records without loading all data.

        For JSONL files, this requires counting non-empty lines.

        Args:
            filename: Path to the JSONL file.

        Returns:
            The total number of records in the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        count = 0
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def get_record_at_index(self, filename: str, index: int) -> dict[str, Any]:
        """Get a specific record by index.

        For JSONL files, this streams through the file until reaching
        the desired index.

        Args:
            filename: Path to the JSONL file.
            index: The zero-based index of the record to load.

        Returns:
            The record at the given index.

        Raises:
            FileNotFoundError: If the file does not exist.
            IndexError: If the index is out of range.

        Examples:
            >>> loader = JSONLLoader()
            >>> record = loader.get_record_at_index("data.jsonl", 5)
            >>> print(record["uuid"])
        """
        if index < 0:
            raise IndexError(f"Record index {index} cannot be negative")

        for i, record in enumerate(self.load(filename)):
            if i == index:
                return record

        raise IndexError(f"Record index {index} out of range")
