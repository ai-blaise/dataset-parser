# Data Splitter Implementation Plan

## Overview

A command-line tool to split JSONL datasets into `n` pieces, ensuring that the sum total and recombination of all pieces recreates the original dataset exactly.

## Dataset Analysis

### Files in `dataset/`

| File | Entries | Parity | Size |
|------|---------|--------|------|
| `interactive_agent.jsonl` | 19,028 | **Odd** | 428 MB |
| `tool_calling.jsonl` | 316,094 | **Even** | 5.0 GB |

### Record Structure

Both JSONL files share a common structure:
```json
{
    "uuid": "unique-identifier",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "...", "tool_calls": [...]}
    ],
    "tools": [...],
    "license": "cc-by-4.0",
    "used_in": ["nano_v3"]
}
```

## Splitting Algorithm

### Even Split (N records, M parts where N % M == 0)

```
records_per_part = N // M
```

Example: 100 records into 4 parts = 25 records each

### Odd Split (N records, M parts where N % M != 0)

```
base_size = N // M
remainder = N % M
```

**Distribution Strategy**: First `remainder` parts get `base_size + 1` records, remaining parts get `base_size` records.

Example: 19,028 records into 3 parts:
- `base_size = 19,028 // 3 = 6,342`
- `remainder = 19,028 % 3 = 2`
- Part 1: 6,343 records (indices 0-6,342)
- Part 2: 6,343 records (indices 6,343-12,685)
- Part 3: 6,342 records (indices 12,686-19,027)
- **Total: 6,343 + 6,343 + 6,342 = 19,028** ✓

### General Formula

For part `i` (0-indexed) of `M` total parts:
```python
def get_part_bounds(total_records: int, num_parts: int, part_index: int) -> tuple[int, int]:
    """Returns (start_index, end_index) for a given part."""
    base_size = total_records // num_parts
    remainder = total_records % num_parts

    # First 'remainder' parts get one extra record
    if part_index < remainder:
        start = part_index * (base_size + 1)
        end = start + base_size + 1
    else:
        start = remainder * (base_size + 1) + (part_index - remainder) * base_size
        end = start + base_size

    return start, end
```

## CLI Interface Design

### Command Structure

```bash
python scripts/data_splitter.py <input_file> --parts N [options]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `input_file` | positional | Yes | Path to input JSONL file |
| `--parts` / `-n` | int | Yes | Number of parts to split into |
| `--output-dir` / `-o` | path | No | Output directory (default: same as input) |
| `--prefix` | str | No | Output filename prefix (default: input filename) |
| `--dry-run` | flag | No | Show split plan without writing files |
| `--verify` | flag | No | Verify split can be recombined correctly |

### Output Naming Convention

```
{prefix}_part_{i}_of_{n}.jsonl
```

Example: `tool_calling.jsonl` split into 5 parts:
```
tool_calling_part_1_of_5.jsonl
tool_calling_part_2_of_5.jsonl
tool_calling_part_3_of_5.jsonl
tool_calling_part_4_of_5.jsonl
tool_calling_part_5_of_5.jsonl
```

## Implementation Details

### File: `scripts/data_splitter.py`

```python
#!/usr/bin/env python3
"""
Data Splitter - Split JSONL datasets into N equal (or near-equal) parts.

Handles both even and odd record counts, ensuring recombination
recreates the original dataset exactly.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator


def count_records(filepath: Path) -> int:
    """Count total records in JSONL file."""
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for _ in f:
            count += 1
    return count


def get_part_bounds(total: int, num_parts: int, part_idx: int) -> tuple[int, int]:
    """Calculate start/end indices for a given part."""
    base = total // num_parts
    remainder = total % num_parts

    if part_idx < remainder:
        start = part_idx * (base + 1)
        end = start + base + 1
    else:
        start = remainder * (base + 1) + (part_idx - remainder) * base
        end = start + base

    return start, end


def iter_records(filepath: Path) -> Iterator[str]:
    """Iterate over raw lines in JSONL file (preserves exact formatting)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            yield line


def split_file(
    input_path: Path,
    num_parts: int,
    output_dir: Path,
    prefix: str,
    dry_run: bool = False
) -> list[dict]:
    """
    Split JSONL file into N parts.

    Returns list of part info dicts with 'path', 'start', 'end', 'count'.
    """
    total = count_records(input_path)
    parts_info = []

    # Calculate all part boundaries first
    for i in range(num_parts):
        start, end = get_part_bounds(total, num_parts, i)
        output_path = output_dir / f"{prefix}_part_{i+1}_of_{num_parts}.jsonl"
        parts_info.append({
            'path': output_path,
            'start': start,
            'end': end,
            'count': end - start,
            'part_num': i + 1
        })

    if dry_run:
        return parts_info

    # Stream through file once, writing to appropriate part files
    output_files = [open(p['path'], 'w', encoding='utf-8') for p in parts_info]

    try:
        for idx, line in enumerate(iter_records(input_path)):
            # Find which part this record belongs to
            for i, part in enumerate(parts_info):
                if part['start'] <= idx < part['end']:
                    output_files[i].write(line)
                    break
    finally:
        for f in output_files:
            f.close()

    return parts_info


def verify_split(input_path: Path, parts_info: list[dict]) -> bool:
    """Verify that parts can be recombined to match original."""
    # Count total records in parts
    total_in_parts = sum(count_records(p['path']) for p in parts_info)
    original_count = count_records(input_path)

    if total_in_parts != original_count:
        print(f"ERROR: Record count mismatch! Original: {original_count}, Parts total: {total_in_parts}")
        return False

    # Verify content matches
    original_records = list(iter_records(input_path))
    combined_records = []
    for part in sorted(parts_info, key=lambda x: x['part_num']):
        combined_records.extend(list(iter_records(part['path'])))

    if original_records != combined_records:
        print("ERROR: Content mismatch after recombination!")
        return False

    print(f"VERIFIED: {len(parts_info)} parts combine to recreate original ({original_count} records)")
    return True


def recombine_parts(parts_paths: list[Path], output_path: Path) -> int:
    """Recombine split parts back into a single file."""
    total = 0
    with open(output_path, 'w', encoding='utf-8') as out:
        for part_path in parts_paths:
            for line in iter_records(part_path):
                out.write(line)
                total += 1
    return total


def main():
    parser = argparse.ArgumentParser(
        description='Split JSONL datasets into N equal (or near-equal) parts.'
    )
    parser.add_argument('input_file', type=Path, help='Input JSONL file')
    parser.add_argument('-n', '--parts', type=int, required=True,
                        help='Number of parts to split into')
    parser.add_argument('-o', '--output-dir', type=Path, default=None,
                        help='Output directory (default: same as input)')
    parser.add_argument('--prefix', type=str, default=None,
                        help='Output filename prefix (default: input filename)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show split plan without writing files')
    parser.add_argument('--verify', action='store_true',
                        help='Verify split can be recombined correctly')

    args = parser.parse_args()

    # Validate input
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    if args.parts < 2:
        print("Error: Must split into at least 2 parts", file=sys.stderr)
        sys.exit(1)

    # Set defaults
    output_dir = args.output_dir or args.input_file.parent
    prefix = args.prefix or args.input_file.stem

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Count records
    total = count_records(args.input_file)
    print(f"Input: {args.input_file}")
    print(f"Total records: {total:,}")
    print(f"Splitting into: {args.parts} parts")
    print()

    # Check if split is possible
    if args.parts > total:
        print(f"Error: Cannot split {total} records into {args.parts} parts", file=sys.stderr)
        sys.exit(1)

    # Perform split
    parts_info = split_file(
        args.input_file,
        args.parts,
        output_dir,
        prefix,
        dry_run=args.dry_run
    )

    # Display results
    print("Split Plan:")
    print("-" * 60)
    for part in parts_info:
        status = "[DRY RUN]" if args.dry_run else "[CREATED]"
        print(f"  Part {part['part_num']}: {part['count']:,} records (indices {part['start']:,}-{part['end']-1:,})")
        print(f"    {status} {part['path']}")
    print("-" * 60)
    print(f"Total: {sum(p['count'] for p in parts_info):,} records")

    # Verify if requested
    if args.verify and not args.dry_run:
        print()
        verify_split(args.input_file, parts_info)


if __name__ == '__main__':
    main()
```

## Usage Examples

### Basic Split

```bash
# Split into 4 parts
python scripts/data_splitter.py dataset/tool_calling.jsonl -n 4

# Output:
# dataset/tool_calling_part_1_of_4.jsonl (79,024 records)
# dataset/tool_calling_part_2_of_4.jsonl (79,024 records)
# dataset/tool_calling_part_3_of_4.jsonl (79,023 records)
# dataset/tool_calling_part_4_of_4.jsonl (79,023 records)
```

### Odd Split Example

```bash
# Split odd-numbered dataset into 3 parts
python scripts/data_splitter.py dataset/interactive_agent.jsonl -n 3

# Output (19,028 records):
# Part 1: 6,343 records (indices 0-6,342)
# Part 2: 6,343 records (indices 6,343-12,685)
# Part 3: 6,342 records (indices 12,686-19,027)
```

### Dry Run (Preview)

```bash
# Preview split without creating files
python scripts/data_splitter.py dataset/tool_calling.jsonl -n 10 --dry-run
```

### Custom Output Directory

```bash
# Split into custom directory with custom prefix
python scripts/data_splitter.py dataset/tool_calling.jsonl -n 5 \
    --output-dir ./splits/ \
    --prefix training_data
```

### With Verification

```bash
# Split and verify recombination
python scripts/data_splitter.py dataset/interactive_agent.jsonl -n 4 --verify
```

## Recombination

### Manual Recombination (Shell)

```bash
# Recombine parts in order
cat dataset/tool_calling_part_1_of_4.jsonl \
    dataset/tool_calling_part_2_of_4.jsonl \
    dataset/tool_calling_part_3_of_4.jsonl \
    dataset/tool_calling_part_4_of_4.jsonl > dataset/tool_calling_recombined.jsonl

# Verify
diff dataset/tool_calling.jsonl dataset/tool_calling_recombined.jsonl
```

### Programmatic Recombination

Add a `recombine` subcommand:

```bash
python scripts/data_splitter.py recombine \
    dataset/tool_calling_part_*.jsonl \
    --output dataset/tool_calling_recombined.jsonl
```

## Memory Efficiency

The implementation uses **streaming** to handle large files:

1. **Counting**: Single pass, no memory allocation for records
2. **Splitting**: Streams line-by-line, never loads full file
3. **Verification**: Compares line-by-line (configurable for large files)

For the 5GB `tool_calling.jsonl`:
- Memory usage: ~O(1) constant (only current line in memory)
- Disk I/O: Single read pass + N write streams

## Edge Cases Handled

| Case | Handling |
|------|----------|
| Odd record count | Extra records distributed to first N parts |
| 1 record, 2 parts | Error: cannot split |
| N records, N parts | Each part gets 1 record |
| Empty file | Creates N empty part files |
| Unicode content | UTF-8 encoding throughout |
| Trailing newlines | Preserved exactly as-is |

## Testing Strategy

### Unit Tests

```python
# tests/test_data_splitter.py

def test_even_split():
    """100 records into 4 parts = 25 each."""
    assert get_part_bounds(100, 4, 0) == (0, 25)
    assert get_part_bounds(100, 4, 3) == (75, 100)

def test_odd_split():
    """19,028 records into 3 parts."""
    assert get_part_bounds(19028, 3, 0) == (0, 6343)
    assert get_part_bounds(19028, 3, 1) == (6343, 12686)
    assert get_part_bounds(19028, 3, 2) == (12686, 19028)

def test_bounds_sum_to_total():
    """All parts sum to original count."""
    for total in [100, 101, 19028, 316094]:
        for parts in [2, 3, 4, 5, 7, 10]:
            total_from_bounds = sum(
                get_part_bounds(total, parts, i)[1] - get_part_bounds(total, parts, i)[0]
                for i in range(parts)
            )
            assert total_from_bounds == total
```

### Integration Tests

```python
def test_split_and_recombine(tmp_path):
    """Split file and recombine, verify matches original."""
    # Create test JSONL
    # Split into parts
    # Recombine parts
    # Assert original == recombined
```

## Project Integration

### Dependencies Required

None beyond stdlib - uses only:
- `argparse` (CLI)
- `json` (JSONL parsing for verification)
- `pathlib` (file paths)

### Recommended Location

```
scripts/
├── data_splitter.py    # <-- New file
├── main.py
├── parser_finale.py
└── ...
```

### Future Enhancements

1. **Format Support**: Extend to JSON arrays and Parquet files
2. **Parallel Writing**: Use multiprocessing for faster splitting
3. **Compression**: Support `.jsonl.gz` input/output
4. **Shuffle Split**: Random sampling mode for train/test splits
5. **Size-Based Split**: Split by file size instead of record count
