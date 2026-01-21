#!/usr/bin/env python3
"""
Forced Tool-Call Rerollout

Preserves the original tool-calling PATTERN from the dataset:
- If original made a tool call → force model to call the SAME tool
- If original had text → let model generate text

This ensures training data keeps good tool-calling behavior even if
the rerollout model is weaker at deciding when to use tools.

WHAT WE FORCE vs WHAT MODEL GENERATES:
┌──────────────────┬─────────────────────┬────────────────────────────────┐
│  Turn Type       │  We Control         │  Model Generates               │
├──────────────────┼─────────────────────┼────────────────────────────────┤
│  Tool Call       │  WHICH tool         │  Tool ARGUMENTS                │
│  Text Response   │  No tools allowed   │  Entire text CONTENT           │
└──────────────────┴─────────────────────┴────────────────────────────────┘

CONTEXT ACCUMULATION (MULTI-TURN):
  Each turn sees all previous turns, including the model's OWN previous outputs.

  Turn 1: context = [system, user]
          → model generates assistant1
          context = [system, user, NEW_assistant1, tool_response]

  Turn 2: context = [system, user, NEW_assistant1, tool_response]
          → model generates assistant2 (sees its OWN assistant1, not original)
          context = [system, user, NEW_assistant1, tool_response, NEW_assistant2]

  This creates coherent multi-turn conversations, not independent regenerations.

Usage:
    uv run python scripts/rerollout_forced.py parsed_datasets/interactive_agent_parsed.jsonl -n 1 -v
    uv run python scripts/rerollout_forced.py input.jsonl -n 100 -o rerolled.jsonl
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
            payload = {
                "model": model,
                "messages": context,
                "tools": tools if tools and orig_tool_calls else None,
                "tool_choice": tool_choice if tools else None,
                "temperature": 0.7,
                "max_tokens": 2048,
            }
            payload = {k: v for k, v in payload.items() if v is not None}

            try:
                resp = requests.post(api_url, json=payload, timeout=120)
                resp.raise_for_status()
                result = resp.json()
                new_assistant = result["choices"][0]["message"]
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

            clean_assistant = {
                "role": "assistant",
                "content": new_assistant.get("content") or ""
            }

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
            else:
                if verbose:
                    content = clean_assistant.get("content", "")[:80]
                    print(f"  -> Content: {content}...")

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
