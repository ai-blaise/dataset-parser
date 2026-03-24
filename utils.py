"""
Streaming utilities for the dataset mixer.

Provides PyArrow-based streaming to avoid OOM with large datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.data_formats import detect_format, get_loader
from scripts.dataset_mixer.adapters import (
    BaseAdapter,
    detect_adapter,
)
from scripts.dataset_mixer.schema import OUTPUT_SCHEMA, TURN_TYPE


def get_source_type(source_dataset: str) -> str:
    """Determine source type for schema transformation.

    Args:
        source_dataset: The source dataset name (e.g., "Nemotron-Terminal-Corpus",
            "Nemotron-SFT-Agentic-v2-search").

    Returns:
        "terminal" for Nemotron-Terminal-Corpus, "agentic" for Nemotron-SFT-Agentic-v2,
        "other" for anything else.
    """
    if "Nemotron-Terminal-Corpus" in source_dataset:
        return "terminal"
    elif "Nemotron-SFT-Agentic-v2" in source_dataset:
        return "agentic"
    return "other"


def transform_terminal_batch(
    batch: pa.RecordBatch, source_dataset: str
) -> pa.RecordBatch:
    """Transform Nemotron Terminal Corpus batch to OUTPUT_SCHEMA.

    Drops 'trial_name' and 'source' columns, adds 'source_dataset'.

    Args:
        batch: Input RecordBatch with Terminal Corpus schema.
        source_dataset: Value for the source_dataset column.

    Returns:
        Transformed RecordBatch conforming to OUTPUT_SCHEMA.
    """
    # Get output field names
    output_fields = [f.name for f in OUTPUT_SCHEMA]

    # Build column data for output
    columns: dict[str, pa.Array] = {}

    for field_name in output_fields:
        if field_name == "source_dataset":
            # Fill with source_dataset value
            columns[field_name] = pa.array(
                [source_dataset] * batch.num_rows, type=pa.string()
            )
        elif field_name in batch.schema.names:
            # Keep existing column
            columns[field_name] = batch.column(field_name)
        else:
            # Fill with nulls
            columns[field_name] = pa.array(
                [None] * batch.num_rows, type=OUTPUT_SCHEMA.field(field_name).type
            )

    # Ensure tools field is present (defaults to None for Terminal)
    if "tools" not in columns:
        columns["tools"] = pa.array([None] * batch.num_rows, type=pa.string())

    return pa.RecordBatch.from_pydict(columns, schema=OUTPUT_SCHEMA)


def transform_agentic_batch(
    batch: pa.RecordBatch, source_dataset: str
) -> pa.RecordBatch:
    """Transform Nemotron-SFT-Agentic-v2 batch to OUTPUT_SCHEMA.

    Handles both search and tool_calling subsets. Renames 'messages' to
    'conversations', extracts model/provider, and sets other fields from
    record metadata.

    Args:
        batch: Input RecordBatch with Agentic v2 schema.
        source_dataset: Value for the source_dataset column (e.g.,
            "Nemotron-SFT-Agentic-v2-search").

    Returns:
        Transformed RecordBatch conforming to OUTPUT_SCHEMA.
    """
    num_rows = batch.num_rows

    # Extract subset name from source_dataset
    subset = source_dataset.split("-")[-1] if "-" in source_dataset else ""

    # Build output columns
    columns: dict[str, pa.Array] = {
        "conversations": batch.column("messages"),
        "agent": pa.array([None] * num_rows, type=pa.string()),
    }

    # Handle model and model_provider
    if "model" in batch.schema.names:
        model_array = batch.column("model")
        columns["model"] = model_array

        # Extract provider from model string
        def extract_provider(model_val):
            if model_val is None:
                return None
            parts = str(model_val).split("/")
            return parts[0] if parts else None

        providers = [extract_provider(m) for m in model_array.to_pylist()]
        columns["model_provider"] = pa.array(providers, type=pa.string())
    else:
        columns["model"] = pa.array([None] * num_rows, type=pa.string())
        columns["model_provider"] = pa.array([None] * num_rows, type=pa.string())

    # date - not present in source
    columns["date"] = pa.array([None] * num_rows, type=pa.string())

    # task - from domain (tool_calling) or used_in (search)
    if "domain" in batch.schema.names:
        columns["task"] = batch.column("domain")
    elif "used_in" in batch.schema.names:
        used_in_col = batch.column("used_in")

        def get_first_used_in(val):
            if val is None:
                return None
            if isinstance(val, list) and val:
                return val[0]
            return None

        tasks = [get_first_used_in(u) for u in used_in_col.to_pylist()]
        columns["task"] = pa.array(tasks, type=pa.string())
    else:
        columns["task"] = pa.array([None] * num_rows, type=pa.string())

    # episode - not present
    columns["episode"] = pa.array([None] * num_rows, type=pa.string())

    # run_id - from uuid
    if "uuid" in batch.schema.names:
        columns["run_id"] = batch.column("uuid")
    else:
        columns["run_id"] = pa.array([None] * num_rows, type=pa.string())

    # enable_thinking - from parallel_tool_calls
    if "parallel_tool_calls" in batch.schema.names:
        columns["enable_thinking"] = batch.column("parallel_tool_calls")
    else:
        columns["enable_thinking"] = pa.array([True] * num_rows, type=pa.bool_())

    # tools - JSON serialize the tools list
    if "tools" in batch.schema.names:
        tools_col = batch.column("tools")

        def serialize_tools(tools_val):
            if tools_val is None:
                return None
            if isinstance(tools_val, list):
                return json.dumps(tools_val)
            return tools_val

        serialized = [serialize_tools(t) for t in tools_col.to_pylist()]
        columns["tools"] = pa.array(serialized, type=pa.string())
    else:
        columns["tools"] = pa.array([None] * num_rows, type=pa.string())

    # source_dataset
    columns["source_dataset"] = pa.array([source_dataset] * num_rows, type=pa.string())

    return pa.RecordBatch.from_pydict(columns, schema=OUTPUT_SCHEMA)


def transform_batch(batch: pa.RecordBatch, source_dataset: str) -> pa.RecordBatch:
    """Transform a RecordBatch to OUTPUT_SCHEMA based on source type.

    Dispatches to the appropriate transform function based on the source
    dataset name.

    Args:
        batch: Input RecordBatch from the source file.
        source_dataset: The source dataset name.

    Returns:
        Transformed RecordBatch conforming to OUTPUT_SCHEMA.
    """
    source_type = get_source_type(source_dataset)

    if source_type == "terminal":
        return transform_terminal_batch(batch, source_dataset)
    elif source_type == "agentic":
        return transform_agentic_batch(batch, source_dataset)
    else:
        # For other sources, try to map columns directly
        return transform_terminal_batch(batch, source_dataset)


def stream_parquet_file(
    filepath: str, source_dataset: str, batch_size: int = 512
) -> Iterator[pa.RecordBatch]:
    """Stream a Parquet file with schema transformation.

    Uses PyArrow's iter_batches for memory-efficient streaming. Yields
    transformed batches conforming to OUTPUT_SCHEMA.

    Args:
        filepath: Path to the input Parquet file.
        source_dataset: The source dataset name.
        batch_size: Number of records per batch (controls memory usage).

    Yields:
        Transformed RecordBatch objects conforming to OUTPUT_SCHEMA.
    """
    pf = pq.ParquetFile(filepath)

    for batch in pf.iter_batches(batch_size=batch_size):
        transformed = transform_batch(batch, source_dataset)
        yield transformed


def stream_file(
    filepath: str,
    source_dataset: str,
    batch_size: int = 512,
    tooling_sample_rate: float | None = None,
    sample_seed: int | None = None,
) -> Iterator[pa.RecordBatch]:
    """Stream a file with format-agnostic transformation.

    Detects the file format and routes to the appropriate handler.
    For Parquet files, uses existing stream_parquet_file().
    For JSONL/JSON files, loads via loader, transforms via adapter, and batches.

    Args:
        filepath: Path to the input file.
        source_dataset: The source dataset name.
        batch_size: Number of records per batch.
        tooling_sample_rate: If set, apply random sampling to Nemotron-SFT-Agentic-v2 tool_calling subset.
        sample_seed: Random seed for reproducible sampling.

    Yields:
        Transformed RecordBatch objects conforming to OUTPUT_SCHEMA.
    """
    fmt = detect_format(filepath)

    # Check if sampling is needed for this file (only tool_calling subset)
    do_sample = (
        source_dataset == "Nemotron-SFT-Agentic-v2-tool_calling"
        and tooling_sample_rate is not None
    )

    if fmt == "parquet":
        # Parquet: use existing optimized path (no sampling for Parquet)
        yield from stream_parquet_file(filepath, source_dataset, batch_size)
    elif fmt in ("jsonl", "json"):
        # JSONL/JSON: load records, transform via adapter, and batch results
        adapter: BaseAdapter = detect_adapter(filepath)
        loader = get_loader(filepath)

        if do_sample:
            # Accumulate all records for sampling
            all_records: list[dict[str, Any]] = []
            for raw_record in loader.load(filepath):
                transformed_records = adapter.transform_records(
                    iter([raw_record]), source_dataset
                )
                for record in transformed_records:
                    all_records.append(record)

            # Apply sampling
            if sample_seed is not None:
                import random

                random.seed(sample_seed)
                random.shuffle(all_records)
            sample_size = int(len(all_records) * tooling_sample_rate)
            sampled_records = all_records[:sample_size]

            # Yield in batches
            batch_records: list[dict[str, Any]] = []
            for record in sampled_records:
                batch_records.append(record)
                if len(batch_records) >= batch_size:
                    yield _dict_list_to_batch(batch_records)
                    batch_records = []
            if batch_records:
                yield _dict_list_to_batch(batch_records)
        else:
            # Stream without sampling (original behavior)
            batch_records: list[dict[str, Any]] = []
            for raw_record in loader.load(filepath):
                # Transform using adapter
                transformed_records = adapter.transform_records(
                    iter([raw_record]), source_dataset
                )
                for record in transformed_records:
                    batch_records.append(record)

                    # Yield batch when full
                    if len(batch_records) >= batch_size:
                        yield _dict_list_to_batch(batch_records)
                        batch_records = []

            # Yield remaining records
            if batch_records:
                yield _dict_list_to_batch(batch_records)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _dict_list_to_batch(records: list[dict[str, Any]]) -> pa.RecordBatch:
    """Convert a list of records to a PyArrow RecordBatch.

    Args:
        records: List of records conforming to OUTPUT_SCHEMA.

    Returns:
        PyArrow RecordBatch.
    """
    columns: dict[str, list[Any]] = {field: [] for field in OUTPUT_SCHEMA.names}

    for record in records:
        for field in OUTPUT_SCHEMA.names:
            columns[field].append(record.get(field))

    # Convert each column to PyArrow array
    arrow_columns = {}
    for field in OUTPUT_SCHEMA.names:
        col_data = columns[field]
        if all(v is None for v in col_data):
            # All nulls - use null type
            arrow_columns[field] = pa.array([None] * len(col_data), type=pa.null())
        elif field == "conversations":
            # Special handling for conversations field: list of struct
            # Each element is a list of {"role": "...", "content": "..."} dicts
            arrays: list[pa.ListArray] = []
            for conv_list in col_data:
                if conv_list is None:
                    arrays.append(pa.array([None], type=pa.list_(TURN_TYPE)))
                else:
                    # Convert list of dicts to two arrays
                    roles = [t.get("role") for t in conv_list]
                    contents = [t.get("content") for t in conv_list]
                    role_array = pa.array(roles, type=pa.string())
                    content_array = pa.array(contents, type=pa.string())
                    struct_arr = pa.StructArray.from_arrays(
                        [content_array, role_array],
                        fields=[
                            pa.field("content", pa.string()),
                            pa.field("role", pa.string()),
                        ],
                    )
                    list_arr = pa.array([struct_arr], type=pa.list_(TURN_TYPE))
                    arrays.append(list_arr)
            # Flatten all into single array
            if arrays:
                arrow_columns[field] = pa.concat_arrays(arrays)
            else:
                arrow_columns[field] = pa.array([], type=pa.list_(TURN_TYPE))
        else:
            # Infer type from first non-null value
            first_non_none = next((v for v in col_data if v is not None), None)
            if first_non_none is None:
                arrow_columns[field] = pa.array([None] * len(col_data), type=pa.null())
            elif isinstance(first_non_none, bool):
                arrow_columns[field] = pa.array(col_data, type=pa.bool_())
            elif isinstance(first_non_none, int):
                arrow_columns[field] = pa.array(col_data, type=pa.int64())
            elif isinstance(first_non_none, float):
                arrow_columns[field] = pa.array(col_data, type=pa.float64())
            elif isinstance(first_non_none, str):
                arrow_columns[field] = pa.array(col_data, type=pa.string())
            elif isinstance(first_non_none, list):
                # Lists/dicts - serialize to JSON string
                serialized = [
                    json.dumps(v) if v is not None else None for v in col_data
                ]
                arrow_columns[field] = pa.array(serialized, type=pa.string())
            elif isinstance(first_non_none, dict):
                # Lists/dicts - serialize to JSON string
                serialized = [
                    json.dumps(v) if v is not None else None for v in col_data
                ]
                arrow_columns[field] = pa.array(serialized, type=pa.string())
            else:
                arrow_columns[field] = pa.array(col_data, type=pa.string())

    return pa.RecordBatch.from_pydict(arrow_columns, schema=OUTPUT_SCHEMA)


def get_existing_record_count(output_path: str) -> int:
    """Get record count from existing output file for resume.

    Args:
        output_path: Path to the output Parquet file.

    Returns:
        Number of records in the existing output file, or 0 if file doesn't
        exist or cannot be read.
    """
    if not Path(output_path).exists():
        return 0

    try:
        pf = pq.ParquetFile(output_path)
        return pf.metadata.num_rows
    except Exception:
        return 0
