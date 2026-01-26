# dataset-parser

An internal tool we built for exploring and transforming datasets containing AI conversation data. Provides CLI tools and an interactive TUI.

## Features
- **CLI Tool** - List, search, and analyze records from the command line
- **Parser Finale** - Transform datasets by removing assistant responses
- **TUI Application** - Interactive terminal interface for browsing datasets
- **Data Splitter** - Split large JSONL datasets into N equal parts for parallel processing
- **Multi-Format Support** - Load data from JSONL, JSON, and Parquet formats with automatic detection

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
python scripts/data_splitter.py dataset/conversations.jsonl -n 4

# Preview split without creating files
python scripts/data_splitter.py dataset/conversations.jsonl -n 10 --dry-run
```

## Usage

### CLI Commands

| Command | Description |
|---------|-------------|
| `list <file>` | Tabular summary of records |
| `show <file> <index>` | View record or specific field |
| `search <file> <query>` | Search text across records |
| `stats <file>` | Dataset statistics |

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
