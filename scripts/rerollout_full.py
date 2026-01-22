#!/usr/bin/env python3
"""
Full Dataset Rerollout with Forced Tool Calling + Thinking Traces

Processes the entire Nemotron Agentic v1 dataset:
- Forces same tool-calling pattern as original
- Captures thinking traces (reasoning_content)
- Saves incrementally (resume-safe)
- Shows progress with tqdm + token/s stats

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

    # With parallel workers
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl -w 4
"""

import json
import argparse
import requests
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from tqdm import tqdm


class TokenStats:
    """Thread-safe token statistics tracker."""
    def __init__(self):
        self.lock = threading.Lock()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.api_calls = 0
        self.start_time = time.time()

    def add(self, prompt: int, completion: int, total: int):
        with self.lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.total_tokens += total
            self.api_calls += 1

    def get_stats(self) -> dict:
        with self.lock:
            elapsed = time.time() - self.start_time
            return {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "api_calls": self.api_calls,
                "elapsed": elapsed,
                "tokens_per_sec": self.total_tokens / elapsed if elapsed > 0 else 0,
                "completion_per_sec": self.completion_tokens / elapsed if elapsed > 0 else 0,
            }


def rerollout_record(record: dict, api_url: str, model: str, token_stats: TokenStats) -> dict:
    """
    Rerollout a single record with forced tool calling + thinking traces.
    Returns the rerolled record.
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

            # Track token usage
            usage = result.get("usage", {})
            token_stats.add(
                prompt=usage.get("prompt_tokens", 0),
                completion=usage.get("completion_tokens", 0),
                total=usage.get("total_tokens", 0)
            )

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


def format_tokens(n: int) -> str:
    """Format token count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="Full dataset rerollout with thinking traces")
    parser.add_argument("input", help="Input JSONL file")
    parser.add_argument("-o", "--output", help="Output JSONL file (default: input_rerolled.jsonl)")
    parser.add_argument("-n", "--num", type=int, help="Limit number of records to process")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run (skip already processed)")
    parser.add_argument("--api-url", default="http://localhost:30000/v1/chat/completions")
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V3.2")
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
    print(f"  Model:   {args.model}")
    print(f"  Output:  {output_path}")
    print(f"  Workers: {args.workers}")
    print(f"  Mode:    Forced tool calling + Thinking traces")
    print("=" * 70)
    print()

    # Initialize stats
    token_stats = TokenStats()
    success_count = 0
    error_count = 0
    write_lock = threading.Lock()
    counter_lock = threading.Lock()

    # Open in append mode for resume support
    mode = "a" if args.resume and output_path.exists() else "w"
    out_f = open(output_path, mode)

    def process_one(record):
        nonlocal success_count, error_count
        uuid = record.get("uuid", "unknown")

        try:
            rerolled = rerollout_record(
                record,
                api_url=args.api_url,
                model=args.model,
                token_stats=token_stats
            )

            with write_lock:
                out_f.write(json.dumps(rerolled) + "\n")
                out_f.flush()

            with counter_lock:
                success_count += 1

            return True, uuid, None

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

            return False, uuid, str(e)

    # Process with tqdm
    with tqdm(total=len(to_process), desc="Rerolling", unit="rec",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:

        def update_postfix():
            stats = token_stats.get_stats()
            pbar.set_postfix_str(
                f"✓{success_count} ✗{error_count} | "
                f"{stats['completion_per_sec']:.0f} tok/s | "
                f"total: {format_tokens(stats['total_tokens'])}"
            )

        if args.workers > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(process_one, r): r for r in to_process}
                for future in as_completed(futures):
                    result = future.result()
                    pbar.update(1)
                    update_postfix()
        else:
            for record in to_process:
                process_one(record)
                pbar.update(1)
                update_postfix()

    out_f.close()

    # Final summary
    stats = token_stats.get_stats()
    print()
    print()
    print("=" * 70)
    print("                         COMPLETED")
    print("=" * 70)
    print(f"  Records processed:  {success_count + error_count}")
    print(f"  Successful:         {success_count}")
    print(f"  Errors:             {error_count}")
    print(f"  Time:               {stats['elapsed']/60:.1f} min")
    print(f"  Rate:               {(success_count + error_count) / stats['elapsed']:.2f} rec/s")
    print()
    print(f"  Prompt tokens:      {format_tokens(stats['prompt_tokens'])}")
    print(f"  Completion tokens:  {format_tokens(stats['completion_tokens'])}")
    print(f"  Total tokens:       {format_tokens(stats['total_tokens'])}")
    print(f"  Tokens/sec:         {stats['tokens_per_sec']:.0f}")
    print(f"  Completion tok/s:   {stats['completion_per_sec']:.0f}")
    print()
    print(f"  Output:             {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
