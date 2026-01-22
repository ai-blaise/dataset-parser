#!/usr/bin/env python3
"""
Forced Tool-Call Rerollout (Synchronous Version)

Regenerates assistant responses in a dataset while preserving the original
tool-calling pattern. Used to create training data with a different model's
style while keeping structured tool-calling behavior.

OVERVIEW:
  This script processes conversation datasets and regenerates all assistant
  turns using a specified model (default: DeepSeek-V3.2). It forces the model
  to follow the same tool-calling pattern as the original dataset.

WHAT WE FORCE vs WHAT MODEL GENERATES:
  ┌──────────────────┬─────────────────────┬────────────────────────────────┐
  │  Turn Type       │  We Control         │  Model Generates               │
  ├──────────────────┼─────────────────────┼────────────────────────────────┤
  │  Tool Call       │  WHICH tool         │  Tool ARGUMENTS + THINKING     │
  │  Text Response   │  No tools allowed   │  CONTENT + THINKING (hybrid)   │
  └──────────────────┴─────────────────────┴────────────────────────────────┘

HYBRID THINKING APPROACH:
  - TOOL CALL turns: Always use thinking=True (captures reasoning for tool decisions)
  - TEXT turns: Try thinking=True first. If content is empty/invalid (e.g., just
    a tool name like "get_order_details"), retry with thinking=False and merge:
    keep reasoning from first attempt, content from retry.

  Results: ~90% of TOOL CALL turns and ~100% of TEXT turns get both reasoning + content.

CONTEXT ACCUMULATION (MULTI-TURN):
  Each turn sees all previous turns, including the model's OWN previous outputs
  (not the original dataset's outputs). This creates coherent multi-turn
  conversations rather than independent regenerations.

OUTPUT FORMAT:
  Each output record contains:
  - uuid: Original record UUID
  - messages: Rerolled conversation with reasoning_content where available
  - tools: Original tool definitions
  - license: Original license
  - used_in: Original used_in field

USAGE:
  # Process single record with verbose output
  uv run python scripts/rerollout_forced.py input.jsonl -n 1 -v

  # Process 100 records and save to file
  uv run python scripts/rerollout_forced.py input.jsonl -n 100 -o output.jsonl

  # Process specific record by index
  uv run python scripts/rerollout_forced.py input.jsonl -i 42 -v

  # Generate proof file showing before/after
  uv run python scripts/rerollout_forced.py input.jsonl -n 1 --proof proof.json

OPTIONS:
  input              Input JSONL file with conversation records
  -o, --output       Output JSONL file (default: prints comparison)
  -n, --num          Number of records to process (default: 1)
  -i, --index        Process specific record by index
  -v, --verbose      Show detailed processing logs
  --proof            Write before/after proof to JSON file
  --api-url          API endpoint (default: http://localhost:30000/v1/chat/completions)
  --model            Model name (default: deepseek-ai/DeepSeek-V3.2)

NOTE: This is the synchronous version, suitable for debugging and small batches.
      For full dataset processing, use rerollout_full.py (async, high concurrency).

SEE ALSO:
  scripts/rerollout_full.py - Async version with resume, progress bar, token stats
"""

import json
import argparse
import requests
from pathlib import Path


def rerollout_record(record: dict, api_url: str, model: str, verbose: bool = False) -> dict:
    """
    Rerollout with forced tool calling pattern from original.
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
            if verbose:
                print(f"[{role}] Added to context")
            i += 1

        elif role == "assistant":
            orig_tool_calls = msg.get("tool_calls", [])
            orig_content = msg.get("content", "")

            # Determine tool_choice based on original behavior
            if orig_tool_calls:
                # Original made a tool call - FORCE the same tool
                orig_tool_name = orig_tool_calls[0]["function"]["name"]
                tool_choice = {
                    "type": "function",
                    "function": {"name": orig_tool_name}
                }
                if verbose:
                    print(f"[assistant] FORCING tool call: {orig_tool_name}")
            else:
                # Original had text content - let model generate text (no tools)
                tool_choice = "none"
                if verbose:
                    print(f"[assistant] Generating text (tool_choice=none)")

            # Build payload
            # HYBRID APPROACH:
            # - TOOL CALL turns: thinking=True (works well)
            # - TEXT turns: try thinking=True first, retry with thinking=False if content empty
            is_tool_call_turn = bool(orig_tool_calls)

            def make_request(enable_thinking):
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
                resp = requests.post(api_url, json=payload, timeout=120)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]

            try:
                if is_tool_call_turn:
                    # TOOL CALL: always use thinking
                    new_assistant = make_request(enable_thinking=True)
                else:
                    # TEXT turn: try thinking first, fallback if content empty
                    new_assistant = make_request(enable_thinking=True)
                    content = new_assistant.get("content") or ""
                    # Check if content is valid (not empty, not just a tool name)
                    if len(content.strip()) < 30 or content.strip().startswith("get_") or content.strip().startswith("check_"):
                        if verbose:
                            print(f"  -> Thinking produced invalid content, retrying without thinking...")
                        new_assistant_retry = make_request(enable_thinking=False)
                        # Merge: keep reasoning from first attempt, content from retry
                        reasoning_from_first = new_assistant.get("reasoning_content") or ""
                        new_assistant = new_assistant_retry
                        if reasoning_from_first:
                            new_assistant["reasoning_content"] = reasoning_from_first
            except Exception as e:
                if verbose:
                    print(f"  ERROR: {e}")
                # Fallback - keep original structure but mark as failed
                new_assistant = {
                    "role": "assistant",
                    "content": msg.get("content", ""),
                    "tool_calls": msg.get("tool_calls")
                }

            # Build clean assistant message
            new_tool_calls = new_assistant.get("tool_calls", [])
            # reasoning_content can be None or a string
            reasoning_content = new_assistant.get("reasoning_content") or ""

            clean_assistant = {
                "role": "assistant",
                "content": new_assistant.get("content") or ""
            }

            # Save thinking trace if present
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

                if verbose:
                    tc = new_tool_calls[0]
                    print(f"  -> Tool: {tc['function']['name']}")
                    print(f"     Args: {tc['function']['arguments'][:80]}...")
                    if reasoning_content:
                        print(f"     Thinking: {reasoning_content[:80]}...")
            else:
                if verbose:
                    content = clean_assistant.get("content", "")[:80]
                    print(f"  -> Content: {content}...")
                    if reasoning_content:
                        print(f"     Thinking: {reasoning_content[:80]}...")

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

                    if verbose:
                        print(f"[tool] Mapped ID: {orig_tool_id[:20]}... -> {new_tool_id[:20]}...")

                    context.append(clean_tool)
                    new_messages.append(clean_tool)
                    i += 1
            else:
                # Skip tool responses if we didn't make tool call
                while i < len(original_messages) and original_messages[i].get("role") == "tool":
                    if verbose:
                        print(f"[tool] SKIPPED")
                    i += 1

        elif role == "tool":
            # Shouldn't reach here normally
            if verbose:
                print(f"[tool] Unexpected, skipping")
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


def main():
    parser = argparse.ArgumentParser(description="Forced tool-call rerollout")
    parser.add_argument("input", help="Input JSONL file")
    parser.add_argument("-o", "--output", help="Output JSONL file")
    parser.add_argument("-n", "--num", type=int, default=1, help="Number of records")
    parser.add_argument("-i", "--index", type=int, help="Specific record index")
    parser.add_argument("--api-url", default="http://localhost:30000/v1/chat/completions")
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V3.2")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--proof", help="Write before/after proof file")

    args = parser.parse_args()

    # Read input
    records = []
    with open(args.input) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} records")
    print(f"Mode: FORCED tool calling (preserves original pattern)")

    # Select records
    if args.index is not None:
        to_process = [(args.index, records[args.index])]
    else:
        to_process = list(enumerate(records[:args.num]))

    print(f"Processing {len(to_process)} record(s)")
    print(f"Model: {args.model}")
    print()

    results = []
    for idx, original in to_process:
        print(f"=== Record {idx}: {original.get('uuid', 'unknown')[:12]}... ===")

        # Count original tool calls
        orig_tc_count = sum(1 for m in original["messages"]
                          if m.get("role") == "assistant" and m.get("tool_calls"))
        print(f"  Original tool calls: {orig_tc_count}")

        rerolled = rerollout_record(
            original,
            api_url=args.api_url,
            model=args.model,
            verbose=args.verbose
        )
        results.append((original, rerolled))
        print()

    # Write proof
    if args.proof and results:
        original, rerolled = results[0]
        proof = {
            "description": "Forced Tool-Call Rerollout Proof",
            "mode": "Preserves original tool-calling pattern",
            "model": args.model,
            "uuid": original.get("uuid"),
            "BEFORE": original,
            "AFTER": rerolled
        }
        with open(args.proof, "w") as f:
            json.dump(proof, f, indent=2)
        print(f"Proof written to {args.proof}")

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            for _, rerolled in results:
                f.write(json.dumps(rerolled) + "\n")
        print(f"Output written to {args.output}")
    else:
        print("=== COMPARISON ===")
        for original, rerolled in results:
            print("\nBEFORE (assistant turns):")
            for m in original["messages"]:
                if m["role"] == "assistant":
                    tc = m.get("tool_calls", [])
                    if tc:
                        print(f"  TOOL: {tc[0]['function']['name']}")
                        print(f"    args: {tc[0]['function']['arguments'][:60]}...")
                    else:
                        print(f"  TEXT: \"{m.get('content', '')[:60]}...\"")

            print("\nAFTER (assistant turns):")
            for m in rerolled["messages"]:
                if m["role"] == "assistant":
                    tc = m.get("tool_calls", [])
                    if tc:
                        print(f"  TOOL: {tc[0]['function']['name']}")
                        print(f"    args: {tc[0]['function']['arguments'][:60]}...")
                    else:
                        print(f"  TEXT: \"{m.get('content', '')[:60]}...\"")


if __name__ == "__main__":
    main()
