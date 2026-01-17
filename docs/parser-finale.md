# Parser Finale

Parser Finale processes JSONL records by modifying assistant messages while preserving the conversation structure.

## Running Parser Finale

```bash
uv run python -m scripts.parser_finale <file> [options]
```

## Transformation Behavior

For each **assistant message**:

| Field | What Happens |
|-------|--------------|
| `content` | **Emptied** (set to `""`) |
| `tool_calls` | **Preserved** as-is |
| `reasoning_content` | **Dropped** (not copied) |

All other messages (system, user, tool) pass through **unchanged**.

## Record-Level Fields

These fields are preserved in the output:

- `uuid` - Record identifier
- `messages` - All messages (assistant messages modified as above)
- `tools` - Full tool definitions
- `license` - License information
- `used_in` - Usage tracking
- `reasoning` - Reasoning flag (if present)

## Options

| Option | Description |
|--------|-------------|
| `-f, --format FORMAT` | Output format: `json`, `jsonl`, `markdown`, `text` (default: json) |
| `-o, --output FILE` | Output file path (default: stdout) |
| `-i, --index N` | Process only record at index N |
| `--start N` | Start index for range processing (default: 0) |
| `--end N` | End index for range processing |
| `--has-tools` | Only include records with tool definitions |
| `--compact` | Compact JSON output (no indentation) |

## Output Formats

### JSON (default)

Pretty-printed JSON array of processed records.

```bash
uv run python -m scripts.parser_finale dataset/file.jsonl -f json
```

### JSONL

One record per line, suitable for streaming or further processing.

```bash
uv run python -m scripts.parser_finale dataset/file.jsonl -f jsonl
```

### Markdown

Human-readable format with headers and formatting.

```bash
uv run python -m scripts.parser_finale dataset/file.jsonl -f markdown
```

### Text

Plain text summary of records.

```bash
uv run python -m scripts.parser_finale dataset/file.jsonl -f text
```

## Examples

### Basic Usage

```bash
# JSON output to stdout (default)
uv run python -m scripts.parser_finale dataset/conversations.jsonl
```

### Single Record

```bash
# Process only record at index 5
uv run python -m scripts.parser_finale dataset/conversations.jsonl -i 5
```

### Range of Records

```bash
# Process records 0-9 (10 records)
uv run python -m scripts.parser_finale dataset/conversations.jsonl --start 0 --end 10
```

### Output to File

```bash
# Save to output.json
uv run python -m scripts.parser_finale dataset/conversations.jsonl -o output.json

# Save as JSONL
uv run python -m scripts.parser_finale dataset/conversations.jsonl -f jsonl -o output.jsonl
```

### Filtering

```bash
# Only records with tools
uv run python -m scripts.parser_finale dataset/conversations.jsonl --has-tools

# Combine with range
uv run python -m scripts.parser_finale dataset/conversations.jsonl --has-tools --start 0 --end 100
```

### Compact Output

```bash
# No indentation (smaller file size)
uv run python -m scripts.parser_finale dataset/conversations.jsonl --compact -o compact.json
```

### Human-Readable Output

```bash
# Markdown format for review
uv run python -m scripts.parser_finale dataset/conversations.jsonl -f markdown -i 0 > record.md
```

## Use Cases

### Extract Training Prompts

Remove model responses to create input-only datasets:

```bash
uv run python -m scripts.parser_finale dataset/training.jsonl -f jsonl -o prompts.jsonl
```

### Analyze Tool Usage

Focus on records with tools:

```bash
uv run python -m scripts.parser_finale dataset/conversations.jsonl --has-tools -f json -o tools_only.json
```

### Create Sample Dataset

Extract a subset for testing:

```bash
uv run python -m scripts.parser_finale dataset/large.jsonl --start 0 --end 100 -o sample.json
```

### Review Specific Record

Examine a single record in detail:

```bash
uv run python -m scripts.parser_finale dataset/conversations.jsonl -i 42 -f markdown
```

## Transformation Example

**Original record:**

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather?"},
    {
      "role": "assistant",
      "content": "Let me check the weather for you.",
      "tool_calls": [{"id": "call_1", "function": {"name": "get_weather"}}],
      "reasoning_content": "User wants weather info, I should use the tool."
    },
    {"role": "tool", "content": "Sunny, 72°F"},
    {"role": "assistant", "content": "The weather is sunny and 72°F."}
  ]
}
```

**Processed record:**

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather?"},
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [{"id": "call_1", "function": {"name": "get_weather"}}]
    },
    {"role": "tool", "content": "Sunny, 72°F"},
    {"role": "assistant", "content": ""}
  ]
}
```

Note:
- Assistant messages are **kept** (not removed)
- `content` is now **empty** (`""`)
- `tool_calls` are **preserved** exactly
- `reasoning_content` is **removed**
