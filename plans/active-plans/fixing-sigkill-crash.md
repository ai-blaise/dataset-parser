# Plan: Fix SIGKILL Crash in Dataset Mixer for Large Datasets

## Overview

@minimax-m2.5: Fix the SIGKILL (OOM killer) crash that occurs when mixing large Nemotron datasets (~380K records from ~5GB input) using PyArrow streaming and adding resume capability.

---

## Background

### Current Problem

When running:
```bash
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/nemotron_full_family.parquet --include Nemotron
```

The process gets killed by the OOM killer (SIGKILL) due to memory exhaustion.

### Source Dataset Sizes

| Source | File | Size | Records |
|--------|------|------|---------|
| Nemotron-Terminal-Corpus | math.parquet | 2.9GB | ~163K |
| Nemotron-Terminal-Corpus | swe.parquet | 1.1GB | ~32K |
| Nemotron-Terminal-Corpus | code.parquet | 816MB | ~32K |
| Nemotron-Terminal-Corpus | synthetic_tasks/ | ~140K | ~140K |
| Nemotron-SFT-Agentic-v2 | search.jsonl | 597MB | ~6K |
| Nemotron-SFT-Agentic-v2 | tool_calling.jsonl | 436MB | ~8K |

**Total input**: ~5.5GB, **Total records**: ~380K

### Current Architecture (Problematic)

```
Record → Python dict → List[dict] → pa.Table.from_pylist() → ParquetWriter.write_table()
```

**Issues**:
1. Each record converted from PyArrow → Python dict → stored in list
2. `pa.Table.from_pylist()` loads entire batch into memory
3. Large input files (2.9GB math.parquet) loaded entirely into memory
4. No streaming - records accumulate before batching
5. No incremental processing - one file at a time would help
6. Output file not flushed properly on SIGKILL (corrupted)

---

## Goals

1. **Use PyArrow streaming** - Avoid Python dict conversion, stream directly from input to output
2. **Constant memory usage** - Only hold one batch at a time (~512 records)
3. **File-by-file processing** - Complete each source file before next, clear memory between files
4. **Add resume capability** - Continue from partial output if interrupted
5. **Proper output flushing** - Ensure output file is valid even if interrupted

---

## Implementation Plan

> **@architect Note**: Some functions should be extracted as reusable helper/util functions rather than all being in `mixer.py`. See "Helper/Util Functions" section below.

### Step 1: Add Resume Support to CLI (`cli.py`)

**Location**: `scripts/dataset_mixer/cli.py`

Add `--resume` flag:
```python
parser.add_argument(
    "--resume",
    action="store_true",
    help="Resume from existing output file if present (skip already-written records)",
)
```

### Step 2: Add Streaming Functions (new `utils.py`)

**Location**: `utils.py` (ROOT DIRECTORY - not in `scripts/dataset_mixer/`)

Create a new module with reusable streaming utilities. See "Helper/Util Functions" section for full function definitions.

- `get_source_type()` - Determine source type from dataset name
- `transform_terminal_batch()` - Transform Terminal Corpus batches
- `transform_agentic_batch()` - Transform Agentic v2 batches  
- `transform_batch()` - Main dispatcher
- `stream_parquet_file()` - Stream Parquet with transform
- `get_existing_record_count()` - Get record count for resume

Then import these in `mixer.py`.

### Step 3: Modify `mix()` for Streaming + Resume (`mixer.py`)

**Location**: `scripts/dataset_mixer/mixer.py`

Modify the `mix()` function:
```python
def mix(
    input_dir: str,
    output_path: str,
    dry_run: bool = False,
    batch_size: int = 512,  # Smaller default for memory
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    sample_rate: float | None = None,
    sample_seed: int | None = None,
    resume: bool = False,
) -> dict[str, Any]:
```

**Key changes**:
1. Use smaller default batch_size (512 instead of 2000)
2. Add resume logic: check existing output file, get record count
3. Skip already-written records when resuming
4. Process files one at a time, clear memory between files
5. Flush output after each batch write
6. Proper error handling with try/finally

### Step 4: Implement Resume Logic

**In `mix()`**:
- Use `get_existing_record_count()` from streaming module
- Track `records_written` for resume point

### Step 5: Add Per-File Progress and Memory Cleanup

**In processing loop**:
- Process each file completely before moving to next
- Use `stream_parquet_file()` from streaming module
- Call `gc.collect()` after each file
- Print per-file progress

### Step 6: Ensure Proper Output Flushing

**In `mix()`**:
- Write batches incrementally with `writer.write_batch()`
- Clear references and call `gc.collect()` after each batch
- Ensure writer is closed in `finally` block

---

## Data Flow After Changes

### Before (OOM):
```
large input file → entire file in memory → Python dicts → list → table → output
```

### After (Streaming):
```
input.parquet → iter_batches(512) → transform batch → write_batch → output
                (constant ~512 records in memory)
```

---

## File Changes Summary

| File | Changes |
|------|---------|
| `cli.py` | Add `--resume` flag |
| `utils.py` | NEW - Streaming utilities at root (helper functions) |
| `mixer.py` | Import utils functions, modify `mix()` for streaming + resume |
| (no changes to `adapters.py` - kept for non-streaming path) |

---

## Usage Examples

```bash
# Full mix (with streaming - constant memory)
uv run python -m scripts.dataset_mixer datasets/ \
  -o output-datasets/nemotron_full_family.parquet \
  --include Nemotron

# Full mix with smaller batches (safer for low memory)
uv run python -m scripts.dataset_mixer datasets/ \
  -o output-datasets/nemotron_full_family.parquet \
  --include Nemotron \
  --batch-size 256

# Resume from partial output
uv run python -m scripts.dataset_mixer datasets/ \
  -o output-datasets/nemotron_full_family.parquet \
  --include Nemotron \
  --resume

# Dry-run to check record counts
uv run python -m scripts.dataset_mixer datasets/ \
  --dry-run \
  --include Nemotron
```

---

## Expected Benefits

1. **Memory**: Constant ~512 records in memory regardless of input size
2. **Reliability**: Resume from partial output if interrupted
3. **Progress**: Per-file progress reporting
4. **Graceful handling**: Continue on individual file errors
5. **Valid output**: Output file properly flushed even on SIGINT

---

## Testing Plan

1. **Test streaming with small dataset**: Verify output matches expected
2. **Test resume**: Interrupt, then resume - verify no duplicates
3. **Test memory**: Monitor with large dataset - verify constant usage
4. **Test partial failure**: Corrupt one input file, verify continues

---

## Status

| Task | Status |
|------|--------|
| Create `utils.py` with helper functions | PENDING |
| Add `--resume` CLI flag in `cli.py` | PENDING |
| Modify `mix()` in `mixer.py` for streaming + resume | PENDING |
| Test streaming with small dataset | PENDING |
| Test resume capability | PENDING |
| Test with full Nemotron family | PENDING |

---

## Helper/Util Functions

> **@architect**: The following functions should be extracted as reusable components in a separate module (e.g., `utils.py` at root) rather than being defined inline in `mixer.py`. This promotes reusability and separation of concerns.

### Functions to Extract

| Function | Purpose | Location |
|----------|---------|----------|
| `get_source_type(source_dataset)` | Determine source type ("terminal", "agentic", "other") from dataset name | `utils.py` |
| `transform_terminal_batch(batch_dict, source_dataset)` | Transform Nemotron Terminal Corpus batch to OUTPUT_SCHEMA | `utils.py` |
| `transform_agentic_batch(batch_dict, source_dataset)` | Transform Nemotron-SFT-Agentic-v2 batch to OUTPUT_SCHEMA | `utils.py` |
| `transform_batch(batch, source_dataset)` | Dispatch to appropriate transform based on source type | `utils.py` |
| `stream_parquet_file(filepath, source_dataset, batch_size)` | Stream a Parquet file with schema transformation | `utils.py` |
| `get_existing_record_count(output_path)` | Get record count from existing output file for resume | `utils.py` |

### Proposed Module Structure

```
dataset-parser/
├── utils.py              # NEW: Streaming and helper utilities (ROOT)
├── scripts/
│   └── dataset_mixer/
│       ├── __init__.py
│       ├── cli.py        # CLI (add --resume flag)
│       ├── mixer.py      # Main mix() function (modified for streaming)
│       ├── adapters.py   # Existing adapters (keep for non-streaming path)
│       └── schema.py     # OUTPUT_SCHEMA
```

### utils.py Functions

Reference only — full implementation details go in the new `utils.py` module.

```python
# utils.py (ROOT DIRECTORY)

def get_source_type(source_dataset: str) -> str:
    """Determine source type for schema transformation."""

def transform_terminal_batch(batch_dict, source_dataset) -> pa.RecordBatch:
    """Transform Terminal Corpus batch to OUTPUT_SCHEMA."""

def transform_agentic_batch(batch_dict, source_dataset) -> pa.RecordBatch:
    """Transform Agentic v2 batch to OUTPUT_SCHEMA."""

def transform_batch(batch: pa.RecordBatch, source_dataset: str) -> pa.RecordBatch:
    """Main transform dispatcher - routes to appropriate transform."""

def stream_parquet_file(filepath, source_dataset, batch_size=512) -> Iterator[pa.RecordBatch]:
    """Stream Parquet file with schema transform."""

def get_existing_record_count(output_path: str) -> int:
    """Get record count from existing output for resume."""
```

---

## Notes

- The streaming approach bypasses the existing adapters - direct PyArrow to PyArrow transformation
- This is more efficient but means we need to handle schema transformation ourselves
- The `--batch-size` flag controls both input batch size and output batch size
- Resume works by reading the existing output's record count and continuing from there
