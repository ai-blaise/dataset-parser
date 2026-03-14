"""
Per-source adapters for the dataset mixer.

Each adapter wraps an existing DataLoader for I/O and applies source-specific
transforms to produce records conforming to the unified conversations-based
OUTPUT_SCHEMA. The normalization target is 'conversations' (Parquet training
convention), NOT 'messages' (TUI convention).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator

from scripts.data_formats.csv_loader import CSVLoader
from scripts.data_formats.format_detector import detect_format, get_loader
from scripts.data_formats.jsonl_loader import JSONLLoader
from scripts.data_formats.parquet_loader import ParquetLoader
from scripts.dataset_mixer.schema import OUTPUT_SCHEMA

# Column names from the output schema (used to fill defaults)
_SCHEMA_FIELDS = [field.name for field in OUTPUT_SCHEMA]

# Columns to drop from Nemotron sources
_NEMOTRON_DROP_COLUMNS = {"trial_name", "source"}


class BaseAdapter(ABC):
  """Abstract base for source adapters."""

  @abstractmethod
  def stream(self, filename: str, source_dataset: str) -> Iterator[dict[str, Any]]:
    """Stream records from a file, transformed to the unified schema.

    Args:
        filename: Path to the source file.
        source_dataset: Value for the source_dataset column.

    Yields:
        Records conforming to OUTPUT_SCHEMA.
    """
    pass


class NemotronAdapter(BaseAdapter):
  """Adapter for Nemotron Terminal Corpus Parquet files (Sources A & B).

  These files already have a 'conversations' column and full metadata.
  Transform is trivial: drop 'trial_name' and 'source', add 'source_dataset'.
  """

  def __init__(self) -> None:
    self._loader = ParquetLoader()

  def stream(self, filename: str, source_dataset: str) -> Iterator[dict[str, Any]]:
    """Stream Nemotron records with column drops and source_dataset added."""
    for record in self._loader.load(filename):
      out: dict[str, Any] = {}
      for field in _SCHEMA_FIELDS:
        if field == "source_dataset":
          out[field] = source_dataset
        elif field in record:
          out[field] = record[field]
        else:
          out[field] = None
      yield out


class MessagesJSONLAdapter(BaseAdapter):
  """Adapter for JSONL files with a 'messages' key (Source C: TeichAI).

  Renames 'messages' to 'conversations' and fills metadata with defaults.
  """

  def __init__(self) -> None:
    self._loader = JSONLLoader()

  def stream(self, filename: str, source_dataset: str) -> Iterator[dict[str, Any]]:
    """Stream JSONL records, renaming messages to conversations."""
    for record in self._loader.load(filename):
      yield {
        "conversations": record.get("messages", []),
        "agent": None,
        "model": "deepseek-ai/DeepSeek-V3.2",
        "model_provider": None,
        "date": None,
        "task": None,
        "episode": None,
        "run_id": None,
        "enable_thinking": True,
        "source_dataset": source_dataset,
      }


class PromptCompletionCSVAdapter(BaseAdapter):
  """Adapter for CSV files with 'prompt'/'completion' columns (Source D: Raiden).

  Constructs a conversations list from the prompt/completion pair and fills
  metadata with defaults.
  """

  def __init__(self) -> None:
    self._loader = CSVLoader()

  def stream(self, filename: str, source_dataset: str) -> Iterator[dict[str, Any]]:
    """Stream CSV records, constructing conversations from prompt/completion."""
    for record in self._loader.load(filename):
      yield {
        "conversations": [
          {"role": "user", "content": record.get("prompt", "")},
          {"role": "assistant", "content": record.get("completion", "")},
        ],
        "agent": None,
        "model": "deepseek-ai/DeepSeek-V3.2",
        "model_provider": None,
        "date": None,
        "task": None,
        "episode": None,
        "run_id": None,
        "enable_thinking": True,
        "source_dataset": source_dataset,
      }


def detect_adapter(filename: str) -> BaseAdapter:
  """Auto-detect the appropriate adapter for a data file.

  Uses file format detection first, then peeks at the first record
  to inspect columns.

  Args:
      filename: Path to the data file.

  Returns:
      An adapter instance appropriate for the file.

  Raises:
      ValueError: If no adapter matches the file's format and columns.
  """
  fmt = detect_format(filename)

  if fmt == "csv":
    return PromptCompletionCSVAdapter()

  if fmt == "parquet":
    import pyarrow.parquet as pq
    schema = pq.read_schema(filename)
    if "conversations" in schema.names:
      return NemotronAdapter()
    raise ValueError(f"Parquet file '{filename}' has no 'conversations' column")

  if fmt in ("jsonl", "json"):
    loader = get_loader(filename)
    for record in loader.load(filename):
      if "messages" in record:
        return MessagesJSONLAdapter()
      break
    raise ValueError(f"JSONL/JSON file '{filename}' has no 'messages' key")

  raise ValueError(f"No adapter available for format '{fmt}'")
