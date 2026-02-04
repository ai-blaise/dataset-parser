# dataset-parser

A dataset exploration and comparison tool with an interactive TUI. Currently optimized for AI conversation datasets, with a vision to become a **general-purpose dataset comparer**.

## Features

- **Interactive TUI** - Browse and compare datasets in a terminal interface
- **Side-by-Side Comparison** - Compare two datasets or original vs. processed records
- **Multi-Format Support** - Load JSONL, JSON, and Parquet with automatic detection
- **Dynamic Schema Detection** - Automatically detects message, ID, and tool fields
- **Diff Highlighting** - Visual comparison of changes between records
- **CLI Tools** - List, search, and analyze records from the command line
- **Data Splitter** - Split large datasets into N parts for parallel processing

## Requirements
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

### Using uv (recommended)

```bash
git clone <repository-url>
cd dataset-parser
uv sync
```

### Using pip

```bash
git clone <repository-url>
cd dataset-parser
pip install -e .
```

## Quick Start

### Browse a dataset interactively

```bash
# Open a single file
uv run python -m scripts.tui.app dataset/conversations.jsonl

# Open a directory (shows file picker)
uv run python -m scripts.tui.app dataset/
```

### Extract prompts (remove assistant responses)

```bash
# Output to stdout
uv run python -m scripts.parser_finale dataset/conversations.jsonl

# Output to a specific file
uv run python -m scripts.parser_finale dataset/conversations.jsonl -o prompts.json

# Output to a directory (creates train_parsed.json)
uv run python -m scripts.parser_finale dataset/train.jsonl -O parsed_datasets/
```

### Split a dataset into parts

```bash
# Split into 4 parts
uv run python -m scripts.data_splitter dataset/conversations.jsonl -n 4

# Preview split without creating files
uv run python -m scripts.data_splitter dataset/conversations.jsonl -n 10 --dry-run
```

## Usage

### CLI Commands

| Command | Description |
|---------|-------------|
| `uv run python -m scripts.main list <file>` | Tabular summary of records |
| `uv run python -m scripts.main show <file> <index>` | View record or specific field |
| `uv run python -m scripts.main search <file> <query>` | Search text across records |
| `uv run python -m scripts.main stats <file>` | Dataset statistics |

### TUI Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Select file / View record details |
| `ESC` / `b` | Go back / Close modal |
| `m` | Show field detail modal |
| `P` | Export all files in directory (File List) |
| `X` | Export all records in file (Record List) |
| `x` | Export current record (Comparison) |
| `s` | Toggle synchronized scrolling |
| `d` | Toggle diff highlighting |
| `q` | Quit |
| Arrow keys | Navigate |

### Parser Finale Formats

| Format | Description |
|--------|-------------|
| `json` | Pretty-printed JSON (default) |
| `jsonl` | One record per line |
| `parquet` | Apache Parquet columnar format |
| `markdown` | Human-readable format |
| `text` | Plain text summary |

## Future Plans

The tool is currently optimized for AI conversation datasets but is designed to become a **general-purpose dataset comparer**:

- **Configurable schema detection** - Support any JSON structure, not just conversations
- **ID-based record matching** - Match records by key field instead of index
- **Pluggable transformations** - Optional processing instead of hardcoded parser_finale
- **Additional formats** - CSV, Excel/XLSX support

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Architecture Overview](docs/architecture.md) - System design and components
- [Record Structure](docs/record-structure.md) - JSONL data format reference
- [CLI Reference](docs/cli.md) - Complete CLI command documentation
- [TUI Guide](docs/tui.md) - Interactive terminal UI guide
- [Parser Finale](docs/parser-finale.md) - Transformation tool documentation
- [Data Splitter](docs/data-splitter.md) - Dataset splitting utility
- [Data Formats](docs/data-formats.md) - Multi-format loading and schema normalization

## Development

### Running Tests

```bash
uv run pytest tests/
```

### Project Structure

```
dataset-parser/
├── scripts/              # Main application code
│   ├── main.py           # CLI tool
│   ├── parser_finale.py  # Transformation engine
│   ├── data_splitter.py  # Dataset splitting utility
│   ├── data_formats/     # Multi-format data loaders
│   │   ├── base.py       # Abstract base loader class
│   │   ├── jsonl_loader.py
│   │   ├── json_loader.py
│   │   ├── parquet_loader.py
│   │   ├── format_detector.py
│   │   ├── schema_normalizer.py
│   │   └── directory_loader.py
│   └── tui/              # Terminal UI
│       ├── app.py        # Main application
│       ├── data_loader.py
│       ├── views/        # Screen components
│       └── widgets/      # Reusable UI widgets
├── tests/                # Test suite
├── docs/                 # Documentation
└── dataset/              # Data files (gitignored)
```

## License

MIT License - see [LICENSE](LICENSE) for details.
