# Data Formats Module

The `scripts/data_formats/` module provides a unified interface for loading datasets from multiple file formats. It supports automatic format detection, lazy loading for memory efficiency, and schema normalization across formats.

## Supported Formats

| Format | Extensions | Description | Memory Model |
|--------|------------|-------------|--------------|
| JSONL | `.jsonl` | One JSON object per line | Streaming (O(1)) |
| JSON | `.json` | JSON array of objects | Full parse required |
| Parquet | `.parquet`, `.pq` | Apache Parquet columnar | Row group batches |

## Quick Start

```python
from scripts.data_formats import get_loader, detect_format

# Auto-detect format and get appropriate loader
loader = get_loader("dataset/conversations.jsonl")

# Stream records one at a time (memory efficient)
for record in loader.load("dataset/conversations.jsonl"):
    print(record["uuid"])

# Load all records with progress callback
def on_progress(count):
    print(f"Loaded {count} records...")

records = loader.load_all("dataset/conversations.jsonl", progress_callback=on_progress)
```

## Format Detection

The module automatically detects file formats based on extension or content:

```python
from scripts.data_formats import detect_format, get_loader

# By extension
format_name = detect_format("data.jsonl")  # Returns 'jsonl'
format_name = detect_format("data.parquet")  # Returns 'parquet'

# Content sniffing for unknown extensions
format_name = detect_format("data.dat")  # Checks file contents
```

### Detection Strategy

1. Check file extension (case-insensitive)
2. If unknown extension, perform content sniffing:
   - Check for Parquet magic bytes (`PAR1` at start)
   - Check first non-whitespace character for JSON (`[` or `{`)

## Loaders

### Base Interface

All loaders implement the `DataLoader` abstract base class:

```python
from scripts.data_formats import DataLoader

class DataLoader(ABC):
    @property
    def format_name(self) -> str: ...
    @property
    def supported_extensions(self) -> list[str]: ...

    def load(self, filename) -> Iterator[dict]: ...
    def load_all(self, filename, max_records=None, progress_callback=None) -> list[dict]: ...
    def get_record_count(self, filename) -> int: ...
    def get_record_at_index(self, filename, index) -> dict: ...
```

### JSONL Loader

Best for large files due to streaming capability.

```python
from scripts.data_formats import JSONLLoader

loader = JSONLLoader()

# Stream records (O(1) memory)
for record in loader.load("data.jsonl"):
    process(record)

# Get record count (single pass)
count = loader.get_record_count("data.jsonl")

# Random access (streams to index)
record = loader.get_record_at_index("data.jsonl", 42)
```

### JSON Loader

Supports both arrays `[{...}, {...}]` and single objects `{...}`.

```python
from scripts.data_formats import JSONLoader

loader = JSONLoader()

# Single objects are wrapped as single-element lists
records = loader.load_all("single_record.json")  # Returns [record]

# Arrays work as expected
records = loader.load_all("array.json")  # Returns [record1, record2, ...]
```

### Parquet Loader

Uses PyArrow for efficient columnar access.

```python
from scripts.data_formats import ParquetLoader

loader = ParquetLoader()

# Record count from metadata (instant, no parsing)
count = loader.get_record_count("data.parquet")

# Efficient random access via row groups
record = loader.get_record_at_index("data.parquet", 1000)

# Nested structures (conversations) are fully converted
for record in loader.load("data.parquet"):
    messages = record["conversations"]  # Properly converted to Python list
```

## Schema Normalization

Different formats use different field names. The normalizer provides a consistent interface:

### Field Mappings

| Standard Field | Parquet Field | Description |
|----------------|---------------|-------------|
| `messages` | `conversations` | Conversation data |
| `uuid` | `trial_name` (fallback) | Unique identifier |
| `tools` | `tools` | Tool definitions |
| `license` | `license` | License info |
| `used_in` | `used_in` | Usage tracking |

### Usage

```python
from scripts.data_formats import normalize_record, denormalize_record, is_normalized

# Normalize a parquet record to standard schema
parquet_record = {"conversations": [...], "trial_name": "abc123"}
normalized = normalize_record(parquet_record, source_format="parquet")
# Result: {"messages": [...], "uuid": "abc123", ...}

# Check if already normalized
if not is_normalized(record):
    record = normalize_record(record, "parquet")

# Convert back to format-specific schema
parquet_record = denormalize_record(normalized, target_format="parquet")
```

### Parquet-Only Metadata Fields

These fields are preserved but only exist in Parquet files:

- `agent`, `model`, `model_provider`
- `date`, `task`, `episode`
- `run_id`, `trial_name`

## Directory Discovery

Find all supported data files in a directory:

```python
from scripts.data_formats import discover_data_files, format_file_size

# Get all data files with metadata
files = discover_data_files("/path/to/data/")
for f in files:
    print(f"{f['name']} ({f['format']}) - {format_file_size(f['size'])}")

# Output:
# conversations.jsonl (jsonl) - 1.2 GB
# training.parquet (parquet) - 450 MB
# export.json (json) - 12 KB
```

## Public API

### Imports

```python
from scripts.data_formats import (
    # Base class
    DataLoader,

    # Format detection
    detect_format,
    get_loader,
    get_loader_for_format,
    EXTENSION_MAP,
    SUPPORTED_FORMATS,

    # Loaders
    JSONLLoader,
    JSONLoader,
    ParquetLoader,

    # Schema normalization
    normalize_record,
    denormalize_record,
    get_standard_fields,
    get_parquet_only_fields,
    is_normalized,

    # Directory utilities
    SUPPORTED_EXTENSIONS,
    discover_data_files,
    format_file_size,
)
```

## Memory Efficiency

### Streaming vs Full Load

| Method | Memory | Use Case |
|--------|--------|----------|
| `load()` | O(1) | Processing large files |
| `load_all()` | O(n) | Need random access |
| `get_record_at_index()` | O(1) | Single record lookup |

### Format-Specific Characteristics

**JSONL:**
- Streaming: One line in memory at a time
- Count: Single pass through file
- Random access: Must stream to index

**JSON:**
- Must parse entire file into memory
- Best for smaller datasets or exports

**Parquet:**
- Record count from file metadata (instant)
- Random access via row group seeking
- Nested structures fully supported
- Uses PyArrow for efficient handling

## Error Handling

All loaders raise standard exceptions:

| Exception | Cause |
|-----------|-------|
| `FileNotFoundError` | File does not exist |
| `ValueError` | Invalid file content or format |
| `IndexError` | Record index out of range |
| `json.JSONDecodeError` | Malformed JSON |
| `pyarrow.ArrowInvalid` | Invalid Parquet file |

## Integration with TUI

The TUI application uses this module for all data loading:

```python
# In scripts/tui/data_loader.py
from scripts.data_formats import get_loader, normalize_record

loader = get_loader(filename)
for record in loader.load(filename):
    normalized = normalize_record(record, loader.format_name)
    # Display in UI...
```

The TUI automatically:
- Detects format from file extension
- Shows format in title bar
- Normalizes all records for consistent display
- Uses async loading for files >100MB
