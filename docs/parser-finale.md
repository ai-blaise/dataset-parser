# Parser Finale

Parser Finale processes dataset records by modifying assistant messages while preserving the conversation structure. It supports multiple input and output formats.

## Supported Formats

### Input Formats

| Format | Extensions | Description |
|--------|------------|-------------|
| JSONL | `.jsonl` | One JSON object per line (default) |
| JSON | `.json` | JSON array of objects |
| Parquet | `.parquet`, `.pq` | Apache Parquet columnar format |

The input format is auto-detected from the file extension, or can be specified with `--input-format`.

### Output Formats

| Format | Description |
|--------|-------------|
| `json` | Pretty-printed JSON array (default) |
| `jsonl` | One JSON object per line |
| `parquet` | Apache Parquet format |
| `markdown` | Human-readable Markdown |
| `text` | Plain text summary |

### Schema Normalization

Records from different sources are normalized to a standard schema:

- Parquet `conversations` is converted to `messages`
- Parquet `trial_name` is used as `uuid` fallback
- Missing fields get default values

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
| `reasoning_content` | **Emptied** (set to `""`) |

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
| `--input-format FORMAT` | Input format: `auto`, `jsonl`, `json`, `parquet` (default: auto) |
| `-f, --format, --output-format FORMAT` | Output format: `json`, `jsonl`, `parquet`, `markdown`, `text` (default: json) |
| `-o, --output FILE` | Output file path (default: stdout, required for parquet output) |
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

### Parquet

Apache Parquet columnar format (requires `-o` output file).

```bash
uv run python -m scripts.parser_finale dataset/file.jsonl -f parquet -o output.parquet
```

## Examples

### Basic Usage

```bash
# JSON output to stdout (default)
uv run python -m scripts.parser_finale dataset/conversations.jsonl
```

### Multi-Format Input

```bash
# Process a Parquet file
uv run python -m scripts.parser_finale dataset/train-00000-of-00001.parquet

# Process a JSON array file
uv run python -m scripts.parser_finale dataset/data.json

# Explicit format (when auto-detection fails)
uv run python -m scripts.parser_finale mydata --input-format jsonl
```

### Format Conversion

```bash
# JSONL to Parquet
uv run python -m scripts.parser_finale data.jsonl -f parquet -o output.parquet

# Parquet to JSONL
uv run python -m scripts.parser_finale data.parquet -f jsonl -o output.jsonl

# Parquet to JSON
uv run python -m scripts.parser_finale data.parquet -f json -o output.json
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
      "tool_calls": [{"id": "call_1", "function": {"name": "get_weather"}}],
      "reasoning_content": ""
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
- `reasoning_content` is **emptied** (set to `""`)
