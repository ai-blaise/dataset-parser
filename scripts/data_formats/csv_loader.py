"""
CSV format data loader.

This module provides the CSVLoader class for loading CSV files
using csv.DictReader for streaming record access.
"""

from __future__ import annotations

import csv
import sys
from typing import Any, Callable, Iterator

from scripts.data_formats.base import DataLoader

# Raise field size limit to handle large completions (up to 124K chars)
csv.field_size_limit(sys.maxsize)


class CSVLoader(DataLoader):
  """Data loader for CSV format.

  CSV files are loaded via csv.DictReader, which yields each row as a
  dictionary keyed by the header columns. The field size limit is raised
  at module load to support very large fields (e.g. Raiden completions
  up to 124K characters).

  Attributes:
      format_name: Returns 'csv'.
      supported_extensions: Returns ['.csv'].
  """

  @property
  def format_name(self) -> str:
    """Return the format name."""
    return "csv"

  @property
  def supported_extensions(self) -> list[str]:
    """Return supported file extensions."""
    return [".csv"]

  def load(self, filename: str) -> Iterator[dict[str, Any]]:
    """Lazily load records from a CSV file.

    Uses csv.DictReader for streaming, yielding one record per row.

    Args:
        filename: Path to the CSV file.

    Yields:
        Each record as a dictionary keyed by column headers.

    Raises:
        FileNotFoundError: If the file does not exist.
        csv.Error: If the CSV is malformed.
    """
    with open(filename, "r", encoding="utf-8", newline="") as f:
      reader = csv.DictReader(f)
      for row in reader:
        yield dict(row)

  def load_all(
    self,
    filename: str,
    max_records: int | None = None,
    progress_callback: Callable[[int, int | None], None] | None = None,
  ) -> list[dict[str, Any]]:
    """Load all records from a CSV file into memory.

    Args:
        filename: Path to the CSV file.
        max_records: Maximum number of records to load (None = all).
        progress_callback: Optional callback(loaded_count, total_count) for
                          progress updates. total_count may be None if unknown.

    Returns:
        A list of all records as dictionaries.

    Raises:
        FileNotFoundError: If the file does not exist.
        csv.Error: If the CSV is malformed.
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

    Counts lines in the file minus the header row. Empty lines are skipped.

    Args:
        filename: Path to the CSV file.

    Returns:
        The total number of data records (excluding header).

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    count = 0
    with open(filename, "r", encoding="utf-8", newline="") as f:
      reader = csv.reader(f)
      next(reader, None)  # Skip header
      for row in reader:
        if any(field.strip() for field in row):
          count += 1
    return count

  def get_record_at_index(self, filename: str, index: int) -> dict[str, Any]:
    """Get a specific record by index.

    Streams through the CSV until reaching the desired index.

    Args:
        filename: Path to the CSV file.
        index: The zero-based index of the record to load.

    Returns:
        The record at the given index.

    Raises:
        FileNotFoundError: If the file does not exist.
        IndexError: If the index is out of range or negative.
    """
    if index < 0:
      raise IndexError(f"Record index {index} cannot be negative")

    for i, record in enumerate(self.load(filename)):
      if i == index:
        return record

    raise IndexError(f"Record index {index} out of range")
