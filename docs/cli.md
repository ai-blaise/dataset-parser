# CLI Tool Reference

The CLI tool (`scripts/main.py`) provides commands for exploring and analyzing JSONL datasets from the command line.

## Running Commands

All commands are run from the project root directory:

```bash
uv run python scripts/main.py <command> [arguments] [options]
```

## Commands

### list

Display a tabular summary of records in the dataset.

```bash
uv run python scripts/main.py list <file> [options]
```

#### Options

| Option | Description |
|--------|-------------|
| `-n, --limit N` | Limit output to N records |
| `--has-tools` | Filter to records with tool definitions |
| `--has-reasoning` | Filter to records with reasoning enabled |
| `--min-messages N` | Filter to records with at least N messages |

#### Output Columns

| Column | Description |
|--------|-------------|
| IDX | Record index (0-based) |
| UUID | Truncated unique identifier |
| MSGS | Number of messages in conversation |
| TOOLS | Number of tool definitions |
| LICENSE | License type |
| USED_IN | Dataset/model usage |
| RSN | Reasoning mode ("on" or "-") |
| PREVIEW | First user message preview |

#### Examples

```bash
# List first 10 records
uv run python scripts/main.py list dataset/conversations.jsonl -n 10

# List records with tools
uv run python scripts/main.py list dataset/conversations.jsonl --has-tools

# List records with at least 5 messages
uv run python scripts/main.py list dataset/conversations.jsonl --min-messages 5

# Combine filters
uv run python scripts/main.py list dataset/conversations.jsonl --has-tools --has-reasoning -n 20
```

---

### show

View a complete record or extract a specific field.

```bash
uv run python scripts/main.py show <file> <index> [options]
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `file` | Path to the JSONL file |
| `index` | Record index (0-based) |

#### Options

| Option | Description |
|--------|-------------|
| `-f, --field PATH` | Extract specific field using dot/bracket notation |

#### Field Path Syntax

Access nested fields using dot notation and array indices:

- `messages` - Get the messages array
- `messages[0]` - Get the first message
- `messages[0].content` - Get content of first message
- `tools[1].function.name` - Get name of second tool's function

#### Examples

```bash
# Show complete record at index 0
uv run python scripts/main.py show dataset/conversations.jsonl 0

# Show only the messages array
uv run python scripts/main.py show dataset/conversations.jsonl 0 -f messages

# Show the second message
uv run python scripts/main.py show dataset/conversations.jsonl 0 -f messages[1]

# Show content of the second message
uv run python scripts/main.py show dataset/conversations.jsonl 0 -f messages[1].content

# Show the UUID
uv run python scripts/main.py show dataset/conversations.jsonl 5 -f uuid

# Show tool definitions
uv run python scripts/main.py show dataset/conversations.jsonl 0 -f tools
```

---

### search

Search for text across all records in the dataset.

```bash
uv run python scripts/main.py search <file> <query> [options]
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `file` | Path to the JSONL file |
| `query` | Search term to find |

#### Options

| Option | Description |
|--------|-------------|
| `-c, --context` | Show matching context around results |
| `--case-sensitive` | Enable case-sensitive matching |
| `-n, --limit N` | Limit number of results |

#### Examples

```bash
# Basic search
uv run python scripts/main.py search dataset/conversations.jsonl "API"

# Search with context shown
uv run python scripts/main.py search dataset/conversations.jsonl "error" -c

# Case-sensitive search
uv run python scripts/main.py search dataset/conversations.jsonl "API" --case-sensitive

# Limit results
uv run python scripts/main.py search dataset/conversations.jsonl "function" -n 5

# Combined options
uv run python scripts/main.py search dataset/conversations.jsonl "Bitcoin" -c -n 10
```

---

### stats

Display statistics about the dataset.

```bash
uv run python scripts/main.py stats <file> [options]
```

#### Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show additional details including top tool names |

#### Output

Basic statistics include:

- Total number of records
- Records with tools
- Records with reasoning
- Message count distribution
- Role distribution (system, user, assistant, tool)

Verbose mode adds:

- Top tool names and their frequency
- License distribution
- Usage tracking breakdown

#### Examples

```bash
# Basic statistics
uv run python scripts/main.py stats dataset/conversations.jsonl

# Verbose statistics with tool breakdown
uv run python scripts/main.py stats dataset/conversations.jsonl -v
```

---

## Parser Finale

The parser finale tool (`scripts/parser_finale.py`) processes dataset records and outputs content with emptied assistant responses.

```bash
uv run python -m scripts.parser_finale <path> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `path` | Path to data file or directory of data files (JSONL, JSON, or Parquet) |

### Options

| Option | Description |
|--------|-------------|
| `--input-format` | Input format: auto, jsonl, json, parquet (default: auto) |
| `-f, --format` | Output format: json, jsonl, parquet, markdown, text (default: json) |
| `-o, --output` | Output file path (default: stdout) |
| `-O, --output-dir` | Output directory for batch processing (default: parsed_datasets) |
| `-i, --index` | Process only record at this index |
| `--start` | Start index for range processing |
| `--end` | End index for range processing |
| `--has-tools` | Only include records with tools |
| `--compact` | Compact JSON output (no indentation) |

### Output Directory Mode

When using `--output-dir` (or `-O`), the tool saves processed output to a file in the specified directory. The output filename follows the pattern: `{original_stem}_parsed.{format}`.

**Example:**
- Input: `dataset/train.jsonl`
- Output: `parsed_datasets/train_parsed.json`

If `-o` (specific output file) is provided, it takes precedence over `--output-dir`.

### Examples

```bash
# Process file to stdout
uv run python -m scripts.parser_finale dataset/train.jsonl

# Process file to output directory
uv run python -m scripts.parser_finale dataset/train.jsonl -O parsed_datasets

# Process to specific file (overrides --output-dir)
uv run python -m scripts.parser_finale dataset/train.jsonl -o output.json

# Process as JSONL format to output directory
uv run python -m scripts.parser_finale dataset/train.jsonl -f jsonl -O parsed_datasets

# Process directory (launches TUI)
uv run python -m scripts.parser_finale dataset/ -O parsed_datasets

# Process only records with tools
uv run python -m scripts.parser_finale dataset/train.jsonl --has-tools -O parsed_datasets
```

---

## Tips

### Large Datasets

For large datasets, use limits to avoid overwhelming output:

```bash
# Sample first 100 records
uv run python scripts/main.py list dataset/large.jsonl -n 100
```

### Field Exploration

Use `show` to explore record structure before writing queries:

```bash
# See full record structure
uv run python scripts/main.py show dataset/file.jsonl 0

# Then drill down
uv run python scripts/main.py show dataset/file.jsonl 0 -f messages[0].role
```
