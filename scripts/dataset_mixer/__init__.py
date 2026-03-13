"""
Dataset mixer package.

Combines multiple dataset sources into a single unified Parquet file
for training. Supports JSONL, CSV, and Parquet inputs with per-source
adapters that normalize to a common conversations-based schema.
"""
