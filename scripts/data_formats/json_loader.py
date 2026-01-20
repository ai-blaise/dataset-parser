"""
JSON format data loader.

This module provides the JSONLoader class for loading JSON files that contain
either an array of objects or a single object.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterator

from scripts.data_formats.base import DataLoader


class JSONLoader(DataLoader):
    """Data loader for JSON format.

    JSON files can contain either:
    - An array of objects: [{...}, {...}, ...]
    - A single object: {...}

    This loader handles both cases, treating a single object as a list
    with one element.

    Attributes:
        format_name: Returns 'json'.
        supported_extensions: Returns ['.json'].
    """

    @property
    def format_name(self) -> str:
        """Return the format name."""
        return "json"

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".json"]

    def _load_json_data(self, filename: str) -> list[dict[str, Any]]:
        """Load JSON file and return as list of records.

        Handles both array and single object formats.

        Args:
            filename: Path to the JSON file.

        Returns:
            A list of records (single object wrapped in list if needed).

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            ValueError: If the JSON is not an object or array of objects.
        """
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle array of objects
        if isinstance(data, list):
            # Validate that all items are dictionaries
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"JSON array item at index {i} is not an object (got {type(item).__name__})"
                    )
            return data

        # Handle single object
        if isinstance(data, dict):
            return [data]

        raise ValueError(
            f"JSON file must contain an object or array of objects (got {type(data).__name__})"
        )

    def load(self, filename: str) -> Iterator[dict[str, Any]]:
        """Load records from a JSON file.

        For JSON files, the entire file must be parsed at once due to the
        format structure. This method yields records one at a time from
        the parsed data.

        Args:
            filename: Path to the JSON file.

        Yields:
            Each record as a dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            ValueError: If the JSON is not an object or array of objects.

        Examples:
            >>> loader = JSONLoader()
            >>> for record in loader.load("data.json"):
            ...     print(record["uuid"])
        """
        data = self._load_json_data(filename)
        for record in data:
            yield record

    def load_all(
        self,
        filename: str,
        max_records: int | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Load all records from a JSON file into memory.

        Args:
            filename: Path to the JSON file.
            max_records: Maximum number of records to load (None = all).
            progress_callback: Optional callback(loaded_count, total_count) for
                              progress updates.

        Returns:
            A list of all records as dictionaries.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            ValueError: If the JSON is not an object or array of objects.

        Examples:
            >>> loader = JSONLoader()
            >>> records = loader.load_all("data.json")
            >>> print(f"Loaded {len(records)} records")
        """
        data = self._load_json_data(filename)
        total_count = len(data)

        if max_records is not None:
            data = data[:max_records]

        if progress_callback is not None:
            # Report progress for consistency with other loaders
            for i in range(0, len(data), 1000):
                progress_callback(min(i + 1000, len(data)), total_count)
            progress_callback(len(data), len(data))

        return data

    def get_record_count(self, filename: str) -> int:
        """Get total number of records.

        For JSON files, this requires parsing the entire file to count records.

        Args:
            filename: Path to the JSON file.

        Returns:
            The total number of records in the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        data = self._load_json_data(filename)
        return len(data)

    def get_record_at_index(self, filename: str, index: int) -> dict[str, Any]:
        """Get a specific record by index.

        For JSON files, this requires parsing the entire file.

        Args:
            filename: Path to the JSON file.
            index: The zero-based index of the record to load.

        Returns:
            The record at the given index.

        Raises:
            FileNotFoundError: If the file does not exist.
            IndexError: If the index is out of range.
            json.JSONDecodeError: If the file contains invalid JSON.

        Examples:
            >>> loader = JSONLoader()
            >>> record = loader.get_record_at_index("data.json", 5)
            >>> print(record["uuid"])
        """
        if index < 0:
            raise IndexError(f"Record index {index} cannot be negative")

        data = self._load_json_data(filename)

        if index >= len(data):
            raise IndexError(f"Record index {index} out of range (0-{len(data) - 1})")

        return data[index]
