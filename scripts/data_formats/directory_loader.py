"""
Directory scanning utilities for discovering data files.

This module provides functions for discovering supported data files
within a directory.
"""

from __future__ import annotations

from pathlib import Path

from scripts.data_formats.format_detector import EXTENSION_MAP

# Supported file extensions (derived from EXTENSION_MAP)
SUPPORTED_EXTENSIONS = frozenset(EXTENSION_MAP.keys())


def discover_data_files(directory: str) -> list[dict]:
    """
    Discover all supported data files in a directory.

    Args:
        directory: Path to the directory to scan.

    Returns:
        List of dicts with:
        - path: absolute path to file
        - name: filename
        - format: detected format (jsonl, json, parquet)
        - size: file size in bytes
    """
    dir_path = Path(directory)
    files = []

    # Iterate all files and check extension case-insensitively
    # (glob patterns are case-sensitive on Linux)
    try:
        for file_path in dir_path.iterdir():
            if not file_path.is_file():
                continue

            # Check extension case-insensitively
            ext_lower = file_path.suffix.lower()
            if ext_lower not in EXTENSION_MAP:
                continue

            try:
                files.append({
                    "path": str(file_path.absolute()),
                    "name": file_path.name,
                    "format": EXTENSION_MAP[ext_lower],
                    "size": file_path.stat().st_size,
                })
            except (OSError, PermissionError):
                # Skip files we can't access
                continue
    except (OSError, PermissionError):
        # Can't read directory
        return []

    # Sort by name for consistent ordering
    return sorted(files, key=lambda f: f["name"].lower())


def format_file_size(size_bytes: int) -> str:
    """Format file size for display (e.g., '1.2 MB').

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string.
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
