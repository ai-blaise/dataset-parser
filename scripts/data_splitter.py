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

# NOTE: in the future there should be a better way to shard the datasets 
# for now this is the easiest way ti do this and take into account
# even & odd counts for number of datasets
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
