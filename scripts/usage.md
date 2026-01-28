# JSONL Dataset Explorer Usage

Run all commands from the project root directory.

## Record Structure

Each JSONL record contains these fields:

| Field | Description |
|-------|-------------|
| `uuid` | Unique identifier for the record |
| `messages` | List of conversation messages (system, user, assistant, tool) |
| `tools` | List of tool/function definitions available to the assistant |
| `license` | License type (e.g., "cc-by-4.0") |
| `used_in` | List of datasets/models this record is used in (e.g., ["nano_v3"]) |
| `reasoning` | Reasoning mode flag (only in interactive_agent.jsonl, value: "on") |

---

## TUI Application

Interactive terminal UI for browsing datasets.

### Running the TUI

```bash
uv run python -m scripts.tui.app dataset/interactive_agent.jsonl
```

### Keybindings

| Key | Action |
|-----|--------|
| `Enter` | View full record details (Messages, Tools, Metadata tabs) |
| `f` | Show field detail modal for current cell |
| `q` | Quit application |
| `ESC` | Close modal / Go back to list |
| `Tab` | Switch tabs in detail view |
| `Arrow keys` | Navigate cells in the table |

### Field Detail Modal

Click on any cell or press `f` to view detailed information for that field:

| Field | Detail View Shows |
|-------|-------------------|
| IDX | Record index with navigation hint |
| UUID | Full UUID (untruncated) |
| MSGS | Message count breakdown by role (system, user, assistant, tool) |
| TOOLS | Scrollable list of all tool names with descriptions |
| LICENSE | Full license name |
| USED_IN | Complete list of usage contexts |
| RSN | Reasoning status and count of messages with reasoning_content |
| PREVIEW | Full first user message content |

---

## Parser Finale

Output JSONL content **without model responses** (assistant messages excluded). Useful for extracting training prompts or analyzing input data.

### What's Included

- `uuid` - Record identifier
- `messages` - Only system, user, and tool messages (no assistant)
- `tools` - Full tool definitions
- `license` - License information
- `used_in` - Usage tracking
- `reasoning` - Reasoning flag (if present)

### What's Excluded

- All `assistant` messages (including tool_calls, content, and reasoning_content)

### Usage

```bash
# Basic usage - JSON output to stdout
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl

# Specific record by index
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -i 5

# Range of records
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --start 0 --end 10

# Different output formats
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -f json      # Pretty JSON (default)
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -f jsonl     # One record per line
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -f markdown  # Human-readable
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -f text      # Plain text summary

# Output to file
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl -o output.json

# Filter records with tools only
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --has-tools

# Compact JSON (no indentation)
uv run python -m scripts.parser_finale dataset/interactive_agent.jsonl --compact
```

### Options

| Option | Description |
|--------|-------------|
| `-f/--format` | Output format: `json`, `jsonl`, `markdown`, `text` (default: json) |
| `-o/--output` | Output file path (default: stdout) |
| `-i/--index` | Process only record at this index |
| `--start` | Start index for range processing (default: 0) |
| `--end` | End index for range processing |
| `--has-tools` | Only include records with tools |
| `--compact` | Compact JSON output (no indentation) |

---

## CLI Tool (main.py)

| Command | Description | Example |
|---------|-------------|---------|
| `list` | Tabular summary of records | `uv run python -m scripts.main list dataset/file.jsonl -n 10` |
| `show` | View record or specific field | `uv run python -m scripts.main show dataset/file.jsonl 0 -f messages[1]` |
| `search` | Find text in records | `uv run python -m scripts.main search dataset/file.jsonl "query" -c` |
| `stats` | Dataset statistics | `uv run python -m scripts.main stats dataset/file.jsonl -v` |

### List Output Columns

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

### Options

#### list
- `-n/--limit` - Limit output
- `--has-tools` - Filter to records with tools
- `--has-reasoning` - Filter to records with reasoning
- `--min-messages N` - Minimum message count

#### show
- `-f/--field` - Extract specific field (supports `messages[0].content` notation)

#### search
- `-c/--context` - Show matching context
- `--case-sensitive` - Case-sensitive matching
- `-n/--limit` - Limit results

#### stats
- `-v/--verbose` - Show top tool names

### Examples

```bash
# List first 10 records
uv run python -m scripts.main list dataset/interactive_agent.jsonl -n 10

# Show the second message of record 0
uv run python -m scripts.main show dataset/interactive_agent.jsonl 0 -f messages[1]

# Search for "Bitcoin" with context
uv run python -m scripts.main search dataset/interactive_agent.jsonl "Bitcoin" -c

# Get full statistics with tool breakdown
uv run python -m scripts.main stats dataset/interactive_agent.jsonl -v
```
