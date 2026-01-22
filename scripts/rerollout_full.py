#!/usr/bin/env python3
"""
Full Dataset Rerollout with Forced Tool Calling + Thinking Traces

Processes the entire Nemotron Agentic v1 dataset:
- Forces same tool-calling pattern as original
- HYBRID thinking approach:
  - TOOL CALL turns: thinking=True (captures reasoning for tool decisions)
  - TEXT turns: try thinking=True first, retry with thinking=False if content
    empty/invalid, merge reasoning from first attempt with content from retry
- Saves incrementally (resume-safe)
- Shows progress with tqdm + token/s stats
- Async with high concurrency (default 3000)

Usage:
    # Full dataset with 3000 concurrent requests
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl

    # Custom concurrency
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl -c 1000

    # Resume from where you left off
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl --resume

    # Limit for testing
    uv run python scripts/rerollout_full.py parsed_datasets/interactive_agent_parsed.jsonl -n 100
"""

import json
import argparse
import asyncio
import aiohttp
import aiofiles
import time
from pathlib import Path
from tqdm.asyncio import tqdm
from dataclasses import dataclass, field
from typing import Optional
import threading


@dataclass
class TokenStats:
    """Thread-safe token statistics tracker."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    api_calls: int = 0
    start_time: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, prompt: int, completion: int, total: int):
        with self._lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.total_tokens += total
            self.api_calls += 1

    def get_stats(self) -> dict:
        with self._lock:
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


async def rerollout_record(
    record: dict,
    api_url: str,
    model: str,
    token_stats: TokenStats,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore
) -> dict:
    """
    Rerollout a single record with forced tool calling + thinking traces.
    """
    async with semaphore:
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

                # HYBRID APPROACH:
                # - TOOL CALL turns: thinking=True (works well)
                # - TEXT turns: try thinking=True first, retry with thinking=False if content empty
                is_tool_call_turn = bool(orig_tool_calls)

                async def make_request(enable_thinking):
                    payload = {
                        "model": model,
                        "messages": context,
                        "tools": tools if tools and orig_tool_calls else None,
                        "tool_choice": tool_choice if tools else None,
                        "temperature": 0.7,
                        "max_tokens": 2048,
                        "chat_template_kwargs": {"thinking": True} if enable_thinking else None,
                    }
                    payload = {k: v for k, v in payload.items() if v is not None}
                    async with session.post(api_url, json=payload) as resp:
                        resp.raise_for_status()
                        result = await resp.json()
                    # Track token usage
                    usage = result.get("usage", {})
                    token_stats.add(
                        prompt=usage.get("prompt_tokens", 0),
                        completion=usage.get("completion_tokens", 0),
                        total=usage.get("total_tokens", 0)
                    )
                    return result["choices"][0]["message"]

                if is_tool_call_turn:
                    # TOOL CALL: always use thinking
                    new_assistant = await make_request(enable_thinking=True)
                else:
                    # TEXT turn: try thinking first, fallback if content empty
                    new_assistant = await make_request(enable_thinking=True)
                    content = new_assistant.get("content") or ""
                    # Check if content is valid (not empty, not just a tool name)
                    if len(content.strip()) < 30 or content.strip().startswith("get_") or content.strip().startswith("check_"):
                        new_assistant_retry = await make_request(enable_thinking=False)
                        # Merge: keep reasoning from first attempt, content from retry
                        reasoning_from_first = new_assistant.get("reasoning_content") or ""
                        new_assistant = new_assistant_retry
                        if reasoning_from_first:
                            new_assistant["reasoning_content"] = reasoning_from_first

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


async def process_record(
    record: dict,
    api_url: str,
    model: str,
    token_stats: TokenStats,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    write_lock: asyncio.Lock,
    out_file,
    counters: dict
):
    """Process a single record and write result."""
    uuid = record.get("uuid", "unknown")

    try:
        rerolled = await rerollout_record(
            record, api_url, model, token_stats, session, semaphore
        )

        async with write_lock:
            await out_file.write(json.dumps(rerolled) + "\n")
            await out_file.flush()

        counters["success"] += 1
        return True, uuid, None

    except Exception as e:
        async with write_lock:
            error_record = {
                "uuid": uuid,
                "error": str(e),
                "original": record
            }
            await out_file.write(json.dumps(error_record) + "\n")
            await out_file.flush()

        counters["error"] += 1
        return False, uuid, str(e)


async def main_async(args):
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
    print(f"  Model:       {args.model}")
    print(f"  Output:      {output_path}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Mode:        Forced tool calling + Thinking traces")
    print("=" * 70)
    print()

    # Initialize
    token_stats = TokenStats()
    counters = {"success": 0, "error": 0}
    semaphore = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()

    # HTTP session with high limits
    connector = aiohttp.TCPConnector(limit=args.concurrency, limit_per_host=args.concurrency)
    timeout = aiohttp.ClientTimeout(total=300)

    mode = "a" if args.resume and output_path.exists() else "w"

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with aiofiles.open(output_path, mode) as out_file:

            # Create tasks
            tasks = [
                process_record(
                    record, args.api_url, args.model,
                    token_stats, session, semaphore, write_lock, out_file, counters
                )
                for record in to_process
            ]

            # Progress bar
            pbar = tqdm(
                total=len(to_process),
                desc="Rerolling",
                unit="rec",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            )

            # Process all tasks
            for coro in asyncio.as_completed(tasks):
                await coro
                pbar.update(1)

                # Update postfix
                stats = token_stats.get_stats()
                pbar.set_postfix_str(
                    f"✓{counters['success']} ✗{counters['error']} | "
                    f"{stats['completion_per_sec']:.0f} tok/s | "
                    f"total: {format_tokens(stats['total_tokens'])}"
                )

            pbar.close()

    # Final summary
    stats = token_stats.get_stats()
    print()
    print()
    print("=" * 70)
    print("                         COMPLETED")
    print("=" * 70)
    print(f"  Records processed:  {counters['success'] + counters['error']}")
    print(f"  Successful:         {counters['success']}")
    print(f"  Errors:             {counters['error']}")
    print(f"  Time:               {stats['elapsed']/60:.1f} min")
    print(f"  Rate:               {(counters['success'] + counters['error']) / stats['elapsed']:.2f} rec/s")
    print()
    print(f"  Prompt tokens:      {format_tokens(stats['prompt_tokens'])}")
    print(f"  Completion tokens:  {format_tokens(stats['completion_tokens'])}")
    print(f"  Total tokens:       {format_tokens(stats['total_tokens'])}")
    print(f"  Tokens/sec:         {stats['tokens_per_sec']:.0f}")
    print(f"  Completion tok/s:   {stats['completion_per_sec']:.0f}")
    print()
    print(f"  Output:             {output_path}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Full dataset rerollout with thinking traces")
    parser.add_argument("input", help="Input JSONL file")
    parser.add_argument("-o", "--output", help="Output JSONL file (default: input_rerolled.jsonl)")
    parser.add_argument("-n", "--num", type=int, help="Limit number of records to process")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run")
    parser.add_argument("--api-url", default="http://localhost:30000/v1/chat/completions")
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V3.2")
    parser.add_argument("-c", "--concurrency", type=int, default=3000, help="Max concurrent requests")

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
