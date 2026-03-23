"""
Core mixing pipeline for the dataset mixer.

Discovers data files, auto-detects adapters, streams records through
transforms, and writes a schema-enforced Parquet output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.data_formats.format_detector import EXTENSION_MAP
from scripts.dataset_mixer.adapters import detect_adapter
from scripts.dataset_mixer.schema import OUTPUT_SCHEMA


def discover_files(input_dir: str) -> list[dict[str, str]]:
    """Recursively discover all supported data files in a directory.

    Args:
        input_dir: Root directory to scan.

    Returns:
        List of dicts with 'path' and 'source_dataset' keys, sorted by path.
        source_dataset is derived from the top-level subdirectory name.
    """
    root = Path(input_dir)
    files: list[dict[str, str]] = []
    supported = frozenset(EXTENSION_MAP.keys())

    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in supported:
            continue

        # Derive source_dataset from the first subdirectory under root
        rel = filepath.relative_to(root)
        source_dataset = rel.parts[0] if len(rel.parts) > 1 else root.name

        # For Nemotron-SFT-Agentic-v2, add filename suffix for per-file filtering
        if source_dataset == "Nemotron-SFT-Agentic-v2":
            source_dataset = f"{source_dataset}-{filepath.stem}"

        files.append(
            {
                "path": str(filepath),
                "source_dataset": source_dataset,
            }
        )

    return files


def _filter_files(
    file_list: list[dict[str, str]],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[dict[str, str]]:
    """Filter a file list by source_dataset name.

    Args:
        file_list: Output from discover_files().
        include: If set, only keep files whose source_dataset is in this list.
        exclude: If set, drop files whose source_dataset is in this list.

    Returns:
        Filtered file list.
    """
    if include is not None:
        include_set = frozenset(include)
        file_list = [
            f
            for f in file_list
            if any(inc in f["source_dataset"] for inc in include_set)
        ]
    if exclude is not None:
        exclude_set = frozenset(exclude)
        file_list = [
            f
            for f in file_list
            if not any(exc in f["source_dataset"] for exc in exclude_set)
        ]
    return file_list


def stream_all(
    input_dir: str,
    file_list: list[dict[str, str]] | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    sample_rate: float | None = None,
    sample_seed: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream all records from all files, transformed to the unified schema.

    Args:
        input_dir: Root directory (used if file_list is None).
        file_list: Optional pre-computed file list from discover_files().
        include: If set, only process files from these source_datasets.
        exclude: If set, skip files from these source_datasets.
        sample_rate: If set, apply random sampling to Nemotron-SFT-Agentic-v2 records.
        sample_seed: Random seed for reproducible sampling.

    Yields:
        Records conforming to OUTPUT_SCHEMA.
    """
    import random

    if file_list is None:
        file_list = discover_files(input_dir)
    file_list = _filter_files(file_list, include, exclude)

    # If sampling enabled, collect Nemotron-Agentic records separately
    if sample_rate is not None:
        nemotron_agentic_records = []
        other_file_list = []

        for file_info in file_list:
            if "Nemotron-SFT-Agentic-v2" in file_info["source_dataset"]:
                try:
                    adapter = detect_adapter(file_info["path"])
                except ValueError:
                    continue
                for record in adapter.stream(
                    file_info["path"], file_info["source_dataset"]
                ):
                    nemotron_agentic_records.append(record)
            else:
                other_file_list.append(file_info)

        # Stream non-Nemotron-Agentic records first
        for file_info in other_file_list:
            try:
                adapter = detect_adapter(file_info["path"])
            except ValueError:
                continue
            yield from adapter.stream(file_info["path"], file_info["source_dataset"])

        # Apply sampling to Nemotron-Agentic records
        if nemotron_agentic_records:
            if sample_seed is not None:
                random.seed(sample_seed)
            random.shuffle(nemotron_agentic_records)
            sample_size = int(len(nemotron_agentic_records) * sample_rate)
            for record in nemotron_agentic_records[:sample_size]:
                yield record
    else:
        # Original behavior - stream all records directly
        for file_info in file_list:
            try:
                adapter = detect_adapter(file_info["path"])
            except ValueError:
                continue
            yield from adapter.stream(file_info["path"], file_info["source_dataset"])


def mix(
    input_dir: str,
    output_path: str,
    dry_run: bool = False,
    batch_size: int = 2_000,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    sample_rate: float | None = None,
    sample_seed: int | None = None,
) -> dict[str, Any]:
    """Run the full mixing pipeline.

    Args:
        input_dir: Directory containing dataset subdirectories.
        output_path: Path for the output Parquet file.
        dry_run: If True, count records per source without writing output.
        batch_size: Number of records per write batch (controls memory usage).
        include: If set, only process files from these source_datasets.
        exclude: If set, skip files from these source_datasets.
        sample_rate: If set, apply random sampling to Nemotron-SFT-Agentic-v2 records.
        sample_seed: Random seed for reproducible sampling.

    Returns:
        Summary dict with keys: total_records, sources (dict of source -> count),
        output_path (None if dry_run).
    """
    file_list = discover_files(input_dir)
    sources: dict[str, int] = {}
    tasks: dict[str, int] = {}
    total = 0

    def _track(record: dict[str, Any]) -> None:
        nonlocal total
        src = record.get("source_dataset", "unknown")
        sources[src] = sources.get(src, 0) + 1
        task = record.get("task")
        if task is not None:
            tasks[task] = tasks.get(task, 0) + 1
        total += 1

    if dry_run:
        for record in stream_all(
            input_dir, file_list, include, exclude, sample_rate, sample_seed
        ):
            _track(record)
        return {
            "total_records": total,
            "sources": sources,
            "tasks": tasks,
            "output_path": None,
        }

    # Stream records into batches and write to Parquet
    writer: pq.ParquetWriter | None = None
    batch: list[dict[str, Any]] = []

    try:
        for record in stream_all(
            input_dir, file_list, include, exclude, sample_rate, sample_seed
        ):
            batch.append(record)
            _track(record)

            if len(batch) >= batch_size:
                table = pa.Table.from_pylist(batch, schema=OUTPUT_SCHEMA)
                if writer is None:
                    writer = pq.ParquetWriter(output_path, OUTPUT_SCHEMA)
                writer.write_table(table)
                batch = []
                print(f"\r  {total:,} records written...", end="", flush=True)

        # Write remaining records
        if batch:
            table = pa.Table.from_pylist(batch, schema=OUTPUT_SCHEMA)
            if writer is None:
                writer = pq.ParquetWriter(output_path, OUTPUT_SCHEMA)
            writer.write_table(table)

        if total > 0:
            print(f"\r  {total:,} records written.   ")
    finally:
        if writer is not None:
            writer.close()

    # Verify output
    if total > 0:
        output_file = pq.ParquetFile(output_path)

        # Record count verification
        output_rows = output_file.metadata.num_rows
        if output_rows != total:
            raise RuntimeError(
                f"Record count mismatch: wrote {total} records but output "
                f"has {output_rows} rows"
            )

        # Schema conformance check
        output_schema = output_file.schema_arrow
        if output_schema != OUTPUT_SCHEMA:
            missing = set(OUTPUT_SCHEMA.names) - set(output_schema.names)
            extra = set(output_schema.names) - set(OUTPUT_SCHEMA.names)
            type_mismatches = []
            for field in OUTPUT_SCHEMA:
                if field.name in output_schema.names:
                    out_field = output_schema.field(field.name)
                    if out_field.type != field.type:
                        type_mismatches.append(
                            f"  {field.name}: expected {field.type}, got {out_field.type}"
                        )
            parts = ["Schema conformance check failed:"]
            if missing:
                parts.append(f"  Missing columns: {missing}")
            if extra:
                parts.append(f"  Extra columns: {extra}")
            if type_mismatches:
                parts.append("  Type mismatches:")
                parts.extend(type_mismatches)
            raise RuntimeError("\n".join(parts))

    return {
        "total_records": total,
        "sources": sources,
        "tasks": tasks,
        "output_path": output_path,
    }
