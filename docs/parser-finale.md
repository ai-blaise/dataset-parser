# Parser Finale

Parser Finale processes JSONL records by removing assistant message content while preserving the overall structure. This is useful for extracting training prompts or analyzing input data without model responses.

## Running Parser Finale

```bash
uv run python -m scripts.parser_finale <file> [options]
```

## What's Included in Output

- `uuid` - Record identifier
- `messages` - Only system, user, and tool messages (assistant messages excluded)
- `tools` - Full tool definitions
- `license` - License information
- `used_in` - Usage tracking
- `reasoning` - Reasoning flag (if present in original)

## What's Excluded

- All `assistant` messages, including:
  - Message content
  - Tool calls
  - Reasoning content

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

## Transformation Details

The parser finale transformation:

1. **Reads** the original record
2. **Preserves** uuid, tools, license, used_in, reasoning fields
3. **Filters** messages to exclude those with `role: "assistant"`
4. **Outputs** the processed record in the specified format

Original record:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "tool_calls": [...]},
    {"role": "tool", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

Processed record:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "tool", "content": "..."}
  ]
}
```
