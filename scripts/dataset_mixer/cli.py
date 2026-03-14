"""
CLI for the dataset mixer.

Usage:
    uv run python -m scripts.dataset_mixer datasets/ -o mixed_output.parquet
    uv run python -m scripts.dataset_mixer datasets/ --dry-run
"""

from __future__ import annotations

import argparse
import sys

from scripts.dataset_mixer.mixer import mix


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(
    prog="dataset_mixer",
    description="Mix multiple datasets into a single unified Parquet file.",
  )
  parser.add_argument(
    "input_dir",
    help="Root directory containing dataset subdirectories",
  )
  parser.add_argument(
    "-o", "--output",
    default="mixed_output.parquet",
    help="Output Parquet file path (default: mixed_output.parquet)",
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Show record counts per source without writing output",
  )
  parser.add_argument(
    "--include",
    nargs="*",
    default=None,
    help="Only include these source_dataset names (subdirectory names under input_dir)",
  )
  parser.add_argument(
    "--exclude",
    nargs="*",
    default=None,
    help="Exclude these source_dataset names from the mix",
  )

  args = parser.parse_args(argv)

  print(f"Input directory: {args.input_dir}")
  if args.dry_run:
    print("Mode: dry-run (no output will be written)\n")
  else:
    print(f"Output: {args.output}\n")

  if args.include:
    print(f"Include: {', '.join(args.include)}")
  if args.exclude:
    print(f"Exclude: {', '.join(args.exclude)}")

  result = mix(
    input_dir=args.input_dir,
    output_path=args.output,
    dry_run=args.dry_run,
    include=args.include,
    exclude=args.exclude,
  )

  # Print summary
  print("Records per source:")
  for source, count in sorted(result["sources"].items()):
    print(f"  {source}: {count:,}")

  if result.get("tasks"):
    print("\nRecords per task:")
    for task, count in sorted(result["tasks"].items(), key=lambda x: -x[1]):
      print(f"  {task}: {count:,}")

  print(f"\nTotal records: {result['total_records']:,}")

  if result["output_path"]:
    print(f"Output written to: {result['output_path']}")


if __name__ == "__main__":
  main()
