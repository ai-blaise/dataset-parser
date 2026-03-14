"""
Parquet format data loader.

This module provides the ParquetLoader class for loading Apache Parquet files.
Parquet is a columnar storage format that supports efficient compression and
encoding schemes.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

import pyarrow.parquet as pq

from scripts.data_formats.base import DataLoader


def _convert_nested_to_python(value: Any) -> Any:
    """Recursively convert PyArrow nested structures to Python native types.

    PyArrow returns special types for nested structures (lists, structs).
    This function converts them to regular Python dicts and lists.

    Args:
        value: A value that may contain PyArrow nested types.

    Returns:
        The value converted to Python native types.
    """
    if value is None:
        return None

    # Handle PyArrow list-like types
    if hasattr(value, "as_py"):
        return value.as_py()

    # Handle regular Python lists (may contain nested PyArrow types)
    if isinstance(value, list):
        return [_convert_nested_to_python(item) for item in value]

    # Handle regular Python dicts (may contain nested PyArrow types)
    if isinstance(value, dict):
        return {k: _convert_nested_to_python(v) for k, v in value.items()}

    return value


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a parquet row to a Python dictionary with proper nested handling.

    Args:
        row: A dictionary representing a parquet row.

    Returns:
        A Python dictionary with all nested structures converted.
    """
    return {key: _convert_nested_to_python(value) for key, value in row.items()}


class ParquetLoader(DataLoader):
    """Data loader for Apache Parquet format.

    Parquet files are columnar storage format that can contain nested
    structures. This loader handles the conversion of nested structures
    (like the 'conversations' column) to Python native types.

    Attributes:
        format_name: Returns 'parquet'.
        supported_extensions: Returns ['.parquet', '.pq'].
    """

    @property
    def format_name(self) -> str:
        """Return the format name."""
        return "parquet"

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".parquet", ".pq"]

    def load(self, filename: str) -> Iterator[dict[str, Any]]:
        """Lazily load records from a Parquet file.

        Reads the parquet file in batches and yields one record at a time
        for memory-efficient processing.

        Args:
            filename: Path to the Parquet file.

        Yields:
            Each record as a dictionary with nested structures converted
            to Python native types.

        Raises:
            FileNotFoundError: If the file does not exist.
            pyarrow.ArrowInvalid: If the file is not a valid Parquet file.

        Examples:
            >>> loader = ParquetLoader()
            >>> for record in loader.load("data.parquet"):
            ...     print(record["conversations"])
        """
        # Read the parquet file
        parquet_file = pq.ParquetFile(filename)

        # Use explicit batch_size to avoid ArrowNotImplementedError
        # with nested struct columns (default reads entire row group)
        for batch in parquet_file.iter_batches(batch_size=1024):
            # Convert batch to Python dictionaries
            batch_dict = batch.to_pydict()

            # Get number of rows in this row group
            num_rows = len(next(iter(batch_dict.values()))) if batch_dict else 0

            # Yield each row as a dictionary
            for i in range(num_rows):
                row = {key: values[i] for key, values in batch_dict.items()}
                yield _row_to_dict(row)

    def load_all(
        self,
        filename: str,
        max_records: int | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Load all records from a Parquet file into memory.

        Args:
            filename: Path to the Parquet file.
            max_records: Maximum number of records to load (None = all).
            progress_callback: Optional callback(loaded_count, total_count) for
                              progress updates.

        Returns:
            A list of all records as dictionaries.

        Raises:
            FileNotFoundError: If the file does not exist.
            pyarrow.ArrowInvalid: If the file is not a valid Parquet file.

        Examples:
            >>> loader = ParquetLoader()
            >>> records = loader.load_all("data.parquet")
            >>> print(f"Loaded {len(records)} records")
        """
        # Get total count for progress reporting
        total_count = self.get_record_count(filename) if progress_callback else None

        records: list[dict[str, Any]] = []

        for i, record in enumerate(self.load(filename)):
            if max_records is not None and i >= max_records:
                break
            records.append(record)
            if progress_callback is not None and i % 1000 == 0:
                progress_callback(i + 1, total_count)

        if progress_callback is not None:
            progress_callback(len(records), len(records))

        return records

    def get_record_count(self, filename: str) -> int:
        """Get total number of records without loading all data.

        Uses Parquet file metadata to get the row count efficiently.

        Args:
            filename: Path to the Parquet file.

        Returns:
            The total number of records in the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        parquet_file = pq.ParquetFile(filename)
        return parquet_file.metadata.num_rows

    def _find_row_group(
        self, parquet_file: pq.ParquetFile, index: int
    ) -> tuple[int, int]:
        """Find the row group and local offset for a global row index.

        Uses row group metadata for O(1) seeking instead of scanning batches.

        Args:
            parquet_file: An open ParquetFile.
            index: The global row index.

        Returns:
            A tuple of (row_group_index, local_offset_within_group).

        Raises:
            IndexError: If the index is out of range.
        """
        cumulative = 0
        for rg_idx in range(parquet_file.metadata.num_row_groups):
            rg_rows = parquet_file.metadata.row_group(rg_idx).num_rows
            if cumulative + rg_rows > index:
                return rg_idx, index - cumulative
            cumulative += rg_rows
        raise IndexError(f"Record index {index} out of range")

    def get_record_at_index(self, filename: str, index: int) -> dict[str, Any]:
        """Get a specific record by index.

        Uses row group metadata to jump directly to the correct row group,
        avoiding sequential scanning of the entire file.

        Args:
            filename: Path to the Parquet file.
            index: The zero-based index of the record to load.

        Returns:
            The record at the given index.

        Raises:
            FileNotFoundError: If the file does not exist.
            IndexError: If the index is out of range.

        Examples:
            >>> loader = ParquetLoader()
            >>> record = loader.get_record_at_index("data.parquet", 5)
            >>> print(record["conversations"])
        """
        if index < 0:
            raise IndexError(f"Record index {index} cannot be negative")

        parquet_file = pq.ParquetFile(filename)
        total_rows = parquet_file.metadata.num_rows

        if index >= total_rows:
            raise IndexError(f"Record index {index} out of range (0-{total_rows - 1})")

        rg_idx, local_offset = self._find_row_group(parquet_file, index)
        table = parquet_file.read_row_group(rg_idx)
        row = table.slice(local_offset, 1).to_pydict()
        return _row_to_dict({key: values[0] for key, values in row.items()})

    def get_records_range(
        self, filename: str, start: int, count: int
    ) -> list[dict[str, Any]]:
        """Load a range of records efficiently using row group metadata.

        Reads only the row groups that overlap with the requested range,
        avoiding full-file scans.

        Args:
            filename: Path to the Parquet file.
            start: The starting row index (0-based).
            count: Number of records to load.

        Returns:
            A list of records as dictionaries.

        Raises:
            FileNotFoundError: If the file does not exist.
            IndexError: If start is out of range.
        """
        if start < 0:
            raise IndexError(f"Start index {start} cannot be negative")

        parquet_file = pq.ParquetFile(filename)
        total_rows = parquet_file.metadata.num_rows

        if start >= total_rows:
            raise IndexError(f"Start index {start} out of range (0-{total_rows - 1})")

        end = min(start + count, total_rows)
        records: list[dict[str, Any]] = []

        # Find which row groups overlap with [start, end)
        cumulative = 0
        for rg_idx in range(parquet_file.metadata.num_row_groups):
            rg_rows = parquet_file.metadata.row_group(rg_idx).num_rows
            rg_start = cumulative
            rg_end = cumulative + rg_rows

            if rg_end <= start:
                cumulative += rg_rows
                continue
            if rg_start >= end:
                break

            # This row group overlaps — read it
            table = parquet_file.read_row_group(rg_idx)
            local_start = max(0, start - rg_start)
            local_end = min(rg_rows, end - rg_start)
            slice_table = table.slice(local_start, local_end - local_start)
            batch_dict = slice_table.to_pydict()

            num_rows = local_end - local_start
            for i in range(num_rows):
                row = {key: values[i] for key, values in batch_dict.items()}
                records.append(_row_to_dict(row))

            cumulative += rg_rows

        return records
