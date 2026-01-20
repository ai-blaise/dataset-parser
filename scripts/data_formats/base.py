"""
Abstract base class for data loaders.

This module defines the DataLoader interface that all format-specific
loaders must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Iterator


class DataLoader(ABC):
    """Abstract base class for loading datasets.

    All format-specific loaders (JSONL, JSON, Parquet) must inherit from
    this class and implement all abstract methods.
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Return the format name (e.g., 'jsonl', 'json', 'parquet')."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions (e.g., ['.jsonl'])."""
        pass

    @abstractmethod
    def load(self, filename: str) -> Iterator[dict[str, Any]]:
        """Lazily load records from file.

        This generator yields one record at a time, making it memory-efficient
        for processing large files.

        Args:
            filename: Path to the file.

        Yields:
            Each record as a dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid.
        """
        pass

    @abstractmethod
    def load_all(
        self,
        filename: str,
        max_records: int | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Load all records from file into memory.

        Args:
            filename: Path to the file.
            max_records: Maximum number of records to load (None = all).
            progress_callback: Optional callback(loaded_count, total_count) for
                              progress updates. total_count may be None if unknown.

        Returns:
            A list of all records as dictionaries.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid.
        """
        pass

    @abstractmethod
    def get_record_count(self, filename: str) -> int:
        """Get total number of records without loading all data.

        Args:
            filename: Path to the file.

        Returns:
            The total number of records in the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        pass

    @abstractmethod
    def get_record_at_index(self, filename: str, index: int) -> dict[str, Any]:
        """Get a specific record by index.

        Args:
            filename: Path to the file.
            index: The zero-based index of the record to load.

        Returns:
            The record at the given index.

        Raises:
            FileNotFoundError: If the file does not exist.
            IndexError: If the index is out of range.
        """
        pass
