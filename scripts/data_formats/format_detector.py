"""
Format detection utilities for data files.

This module provides functions to detect file formats and get appropriate loaders.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.data_formats.base import DataLoader


# Mapping of file extensions to format names
EXTENSION_MAP: dict[str, str] = {
    ".jsonl": "jsonl",
    ".json": "json",
    ".parquet": "parquet",
    ".pq": "parquet",
}

# Supported format names
SUPPORTED_FORMATS = frozenset(["jsonl", "json", "parquet"])


def detect_format(filename: str) -> str:
    """Detect file format from extension or content.

    Args:
        filename: Path to the file.

    Returns:
        Format name: "jsonl", "json", or "parquet"

    Raises:
        ValueError: If the format cannot be determined or is unsupported.

    Examples:
        >>> detect_format("data.jsonl")
        'jsonl'
        >>> detect_format("data.parquet")
        'parquet'
        >>> detect_format("records.json")
        'json'
    """
    extension = Path(filename).suffix.lower()

    if extension in EXTENSION_MAP:
        return EXTENSION_MAP[extension]

    # Content sniffing for ambiguous cases (no extension or unknown extension)
    path = Path(filename)
    if path.exists():
        # Check for Parquet magic bytes (PAR1)
        try:
            with open(filename, "rb") as f:
                magic = f.read(4)
                if magic == b"PAR1":
                    return "parquet"
        except (IOError, OSError):
            pass

        # Try to determine if it's JSON or JSONL by checking first non-whitespace char
        try:
            with open(filename, "r", encoding="utf-8") as f:
                first_char = None
                for char in f.read(1024):
                    if not char.isspace():
                        first_char = char
                        break

                if first_char == "[":
                    return "json"
                elif first_char == "{":
                    return "jsonl"
        except (IOError, OSError, UnicodeDecodeError):
            pass

    raise ValueError(
        f"Cannot determine format for '{filename}'. "
        f"Supported extensions: {', '.join(sorted(EXTENSION_MAP.keys()))}"
    )


def get_loader(filename: str) -> "DataLoader":
    """Factory function to get appropriate loader for a file.

    Args:
        filename: Path to the file.

    Returns:
        A DataLoader instance appropriate for the file format.

    Raises:
        ValueError: If the format cannot be determined or is unsupported.

    Examples:
        >>> loader = get_loader("data.jsonl")
        >>> for record in loader.load("data.jsonl"):
        ...     print(record)
    """
    # Import loaders here to avoid circular imports
    from scripts.data_formats.json_loader import JSONLoader
    from scripts.data_formats.jsonl_loader import JSONLLoader
    from scripts.data_formats.parquet_loader import ParquetLoader

    format_type = detect_format(filename)

    loaders: dict[str, DataLoader] = {
        "jsonl": JSONLLoader(),
        "json": JSONLoader(),
        "parquet": ParquetLoader(),
    }

    return loaders[format_type]


def get_loader_for_format(format_name: str) -> "DataLoader":
    """Get a loader for a specific format name.

    Args:
        format_name: The format name ("jsonl", "json", or "parquet").

    Returns:
        A DataLoader instance for the specified format.

    Raises:
        ValueError: If the format name is not supported.

    Examples:
        >>> loader = get_loader_for_format("parquet")
        >>> loader.format_name
        'parquet'
    """
    # Import loaders here to avoid circular imports
    from scripts.data_formats.json_loader import JSONLoader
    from scripts.data_formats.jsonl_loader import JSONLLoader
    from scripts.data_formats.parquet_loader import ParquetLoader

    if format_name not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format '{format_name}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    loaders: dict[str, DataLoader] = {
        "jsonl": JSONLLoader(),
        "json": JSONLoader(),
        "parquet": ParquetLoader(),
    }

    return loaders[format_name]
