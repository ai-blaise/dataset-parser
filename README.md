# data-gen

A toolkit for exploring and transforming JSONL datasets containing AI conversation data. Provides CLI tools, a transformation engine, and an interactive terminal UI.

## Features

- **CLI Tool** - List, search, and analyze records from the command line
- **Parser Finale** - Transform datasets by removing assistant responses
- **TUI Application** - Interactive terminal interface for browsing datasets

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

### Using uv (recommended)

```bash
git clone <repository-url>
cd data-gen
uv sync
```

### Using pip

```bash
git clone <repository-url>
cd data-gen
pip install -e .
```

## Quick Start

### Browse a dataset interactively

```bash
uv run python -m scripts.tui.app dataset/conversations.jsonl
```

### List records

```bash
uv run python scripts/main.py list dataset/conversations.jsonl -n 10
```

### View a specific record

```bash
uv run python scripts/main.py show dataset/conversations.jsonl 0
```

### Search for content

```bash
uv run python scripts/main.py search dataset/conversations.jsonl "query" -c
```

### Get dataset statistics

```bash
uv run python scripts/main.py stats dataset/conversations.jsonl -v
```

### Extract prompts (remove assistant responses)

```bash
uv run python -m scripts.parser_finale dataset/conversations.jsonl -o prompts.json
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
| `Enter` | View full record details |
| `f` | Show field detail modal |
| `q` | Quit |
| `ESC` | Close modal / Go back |
| Arrow keys | Navigate |

### Parser Finale Formats

| Format | Description |
|--------|-------------|
| `json` | Pretty-printed JSON (default) |
| `jsonl` | One record per line |
| `markdown` | Human-readable format |
| `text` | Plain text summary |

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Architecture Overview](docs/architecture.md) - System design and components
- [Record Structure](docs/record-structure.md) - JSONL data format reference
- [CLI Reference](docs/cli.md) - Complete CLI command documentation
- [TUI Guide](docs/tui.md) - Interactive terminal UI guide
- [Parser Finale](docs/parser-finale.md) - Transformation tool documentation

## Development

### Running Tests

```bash
uv run pytest tests/
```

### Project Structure

```
data-gen/
├── scripts/           # Main application code
│   ├── main.py        # CLI tool
│   ├── parser_finale.py  # Transformation engine
│   └── tui/           # Terminal UI
├── tests/             # Test suite
├── docs/              # Documentation
└── dataset/           # Data files (gitignored)
```

## License

MIT License - see [LICENSE](LICENSE) for details.
