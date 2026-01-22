#!/usr/bin/env python3
"""
Full Dataset Rerollout with Forced Tool Calling + Thinking Traces

Processes the entire Nemotron Agentic v1 dataset:
- Forces same tool-calling pattern as original
- Captures thinking traces (reasoning_content)
- Saves incrementally (resume-safe)
- Shows progress

WHAT WE FORCE vs WHAT MODEL GENERATES:
┌──────────────────┬─────────────────────┬────────────────────────────────┐
│  Turn Type       │  We Control         │  Model Generates               │
├──────────────────┼─────────────────────┼────────────────────────────────┤
│  Tool Call       │  WHICH tool         │  Tool ARGUMENTS + THINKING     │
│  Text Response   │  No tools allowed   │  CONTENT + THINKING            │
└──────────────────┴─────────────────────┴────────────────────────────────┘

Usage:
    # Full dataset
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl

    # Resume from where you left off
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl --resume

    # Limit for testing
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl -n 100

    # Custom output
    uv run python scripts/rerollout_full.py input.jsonl -o custom_output.jsonl
"""

import json
import argparse
import requests
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


def rerollout_record(record: dict, api_url: str, model: str) -> dict:
    """
    Rerollout a single record with forced tool calling + thinking traces.
    """
    original_messages = record.get("messages", [])
    tools = record.get("tools", [])

    context = []
    new_messages = []
    tool_id_map = {}

    i = 0
    while i < len(original_messages):
        msg = original_messages[i]
        role = msg.get("role")

        if role == "system" or role == "user":
            clean_msg = {"role": role, "content": msg.get("content", "")}
            context.append(clean_msg)
            new_messages.append(clean_msg)
            i += 1

        elif role == "assistant":
            orig_tool_calls = msg.get("tool_calls", [])

            # Determine tool_choice based on original behavior
            if orig_tool_calls:
                orig_tool_name = orig_tool_calls[0]["function"]["name"]
                tool_choice = {
                    "type": "function",
                    "function": {"name": orig_tool_name}
                }
            else:
                tool_choice = "none"

            # Build payload
            payload = {
                "model": model,
                "messages": context,
                "tools": tools if tools and orig_tool_calls else None,
                "tool_choice": tool_choice if tools else None,
                "temperature": 0.7,
                "max_tokens": 2048,
                "chat_template_kwargs": {"thinking": True},
            }
            payload = {k: v for k, v in payload.items() if v is not None}

            # Make request
            resp = requests.post(api_url, json=payload, timeout=180)
            resp.raise_for_status()
            result = resp.json()
            new_assistant = result["choices"][0]["message"]

            # Build clean assistant message
            new_tool_calls = new_assistant.get("tool_calls", [])
            reasoning_content = new_assistant.get("reasoning_content") or ""

            clean_assistant = {
                "role": "assistant",
                "content": new_assistant.get("content") or ""
            }

            if reasoning_content:
                clean_assistant["reasoning_content"] = reasoning_content

            if new_tool_calls:
                clean_assistant["tool_calls"] = new_tool_calls

                # Map tool_call_ids
                for j, new_tc in enumerate(new_tool_calls):
                    if j < len(orig_tool_calls):
                        orig_id = orig_tool_calls[j].get("id")
                        new_id = new_tc.get("id")
                        if orig_id and new_id:
                            tool_id_map[orig_id] = new_id

            context.append(clean_assistant)
            new_messages.append(clean_assistant)
            i += 1

            # Handle subsequent tool responses
            if new_tool_calls:
                while i < len(original_messages) and original_messages[i].get("role") == "tool":
                    tool_msg = original_messages[i]
                    orig_tool_id = tool_msg.get("tool_call_id")
                    new_tool_id = tool_id_map.get(orig_tool_id, new_tool_calls[0].get("id"))

                    clean_tool = {
                        "role": "tool",
                        "tool_call_id": new_tool_id,
                        "content": tool_msg.get("content", "")
                    }

                    context.append(clean_tool)
                    new_messages.append(clean_tool)
                    i += 1
            else:
                while i < len(original_messages) and original_messages[i].get("role") == "tool":
                    i += 1

        elif role == "tool":
            i += 1
        else:
            i += 1

    return {
        "uuid": record.get("uuid"),
        "messages": new_messages,
        "tools": tools,
        "license": record.get("license"),
        "used_in": record.get("used_in", []),
    }


def load_processed_uuids(output_path: Path) -> set:
    """Load UUIDs that have already been processed."""
    processed = set()
    if output_path.exists():
        with open(output_path) as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if record.get("uuid"):
                            processed.add(record["uuid"])
                    except:
                        pass
    return processed


def format_time(seconds: float) -> str:
    """Format seconds as human readable time."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def main():
    parser = argparse.ArgumentParser(description="Full dataset rerollout with thinking traces")
    parser.add_argument("input", help="Input JSONL file")
    parser.add_argument("-o", "--output", help="Output JSONL file (default: input_rerolled.jsonl)")
    parser.add_argument("-n", "--num", type=int, help="Limit number of records to process")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run (skip already processed)")
    parser.add_argument("--api-url", default="http://localhost:30000/v1/chat/completions")
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V3.2")
    parser.add_argument("--stats-every", type=int, default=10, help="Show stats every N records")
    parser.add_argument("-w", "--workers", type=int, default=1, help="Number of parallel workers")

    args = parser.parse_args()

    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_rerolled.jsonl"

    # Load input records
    print(f"Loading {input_path}...")
    records = []
    with open(input_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    total_records = len(records)
    print(f"Loaded {total_records} records")

    # Limit if specified
    if args.num:
        records = records[:args.num]
        print(f"Limited to {len(records)} records")

    # Check for resume
    processed_uuids = set()
    if args.resume and output_path.exists():
        processed_uuids = load_processed_uuids(output_path)
        print(f"Resuming: {len(processed_uuids)} already processed")

    # Filter out already processed
    to_process = [r for r in records if r.get("uuid") not in processed_uuids]
    print(f"To process: {len(to_process)} records")

    if not to_process:
        print("Nothing to process!")
        return

    print()
    print("=" * 70)
    print(f"  Model: {args.model}")
    print(f"  Output: {output_path}")
    print(f"  Workers: {args.workers}")
    print(f"  Mode: Forced tool calling + Thinking traces")
    print("=" * 70)
    print()

    # Process records
    start_time = time.time()
    success_count = 0
    error_count = 0
    done_count = 0
    last_uuid = ""

    # Thread safety
    write_lock = threading.Lock()
    counter_lock = threading.Lock()

    # Open in append mode for resume support
    mode = "a" if args.resume and output_path.exists() else "w"
    out_f = open(output_path, mode)

    def process_one(record):
        nonlocal success_count, error_count, done_count, last_uuid
        uuid = record.get("uuid", "unknown")

        try:
            rerolled = rerollout_record(
                record,
                api_url=args.api_url,
                model=args.model
            )

            with write_lock:
                out_f.write(json.dumps(rerolled) + "\n")
                out_f.flush()

            with counter_lock:
                success_count += 1
                done_count += 1
                last_uuid = uuid[:12]

            return True, uuid

        except Exception as e:
            with write_lock:
                error_record = {
                    "uuid": record.get("uuid"),
                    "error": str(e),
                    "original": record
                }
                out_f.write(json.dumps(error_record) + "\n")
                out_f.flush()

            with counter_lock:
                error_count += 1
                done_count += 1
                last_uuid = uuid[:12]

            return False, uuid

    def update_progress():
        total = len(to_process)
        while done_count < total:
            with counter_lock:
                done = done_count
                succ = success_count
                err = error_count
                uuid = last_uuid

            pct = done / total * 100 if total > 0 else 0
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0

            bar_width = 30
            filled = int(bar_width * done / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_width - filled)

            sys.stdout.write(f"\r[{bar}] {done}/{total} ({pct:.1f}%) | "
                           f"{uuid}... | "
                           f"✓{succ} ✗{err} | "
                           f"{rate:.2f}/s | ETA: {format_time(eta)}  ")
            sys.stdout.flush()
            time.sleep(0.5)

    # Start progress thread
    progress_thread = threading.Thread(target=update_progress, daemon=True)
    progress_thread.start()

    # Process with thread pool
    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(process_one, r) for r in to_process]
            for future in as_completed(futures):
                pass  # Results handled in process_one
    else:
        for record in to_process:
            process_one(record)

    out_f.close()

    # Wait for final progress update
    time.sleep(0.6)

    # Final summary
    elapsed = time.time() - start_time
    print()
    print()
    print("=" * 70)
    print("                         COMPLETED")
    print("=" * 70)
    print(f"  Total processed: {success_count + error_count}")
    print(f"  Successful:      {success_count}")
    print(f"  Errors:          {error_count}")
    print(f"  Time:            {format_time(elapsed)}")
    print(f"  Rate:            {(success_count + error_count) / elapsed:.2f} records/sec")
    print(f"  Output:          {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
