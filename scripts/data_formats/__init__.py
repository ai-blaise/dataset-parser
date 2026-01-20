"""
Data formats module for multi-format dataset loading.

This module provides a unified interface for loading datasets from various
file formats including JSONL, JSON, and Parquet.

Usage:
    from scripts.data_formats import get_loader, normalize_record

    # Auto-detect format and get appropriate loader
    loader = get_loader("data.parquet")
    for record in loader.load("data.parquet"):
        normalized = normalize_record(record, loader.format_name)
        print(normalized["messages"])

    # Or detect format explicitly
    from scripts.data_formats import detect_format
    format_name = detect_format("data.jsonl")  # Returns 'jsonl'
"""

from scripts.data_formats.base import DataLoader
from scripts.data_formats.format_detector import (
    EXTENSION_MAP,
    SUPPORTED_FORMATS,
    detect_format,
    get_loader,
    get_loader_for_format,
)
from scripts.data_formats.json_loader import JSONLoader
from scripts.data_formats.jsonl_loader import JSONLLoader
from scripts.data_formats.parquet_loader import ParquetLoader
from scripts.data_formats.schema_normalizer import (
    denormalize_record,
    get_parquet_only_fields,
    get_standard_fields,
    is_normalized,
    normalize_record,
)

__all__ = [
    # Base class
    "DataLoader",
    # Format detection
    "detect_format",
    "get_loader",
    "get_loader_for_format",
    "EXTENSION_MAP",
    "SUPPORTED_FORMATS",
    # Schema normalization
    "normalize_record",
    "denormalize_record",
    "get_standard_fields",
    "get_parquet_only_fields",
    "is_normalized",
    # Loaders
    "JSONLLoader",
    "JSONLoader",
    "ParquetLoader",
]
