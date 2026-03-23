# dataset-parser

A dataset exploration and comparison tool with an interactive TUI. Currently optimized for AI conversation datasets, with a vision to become a **general-purpose dataset comparer**.

## Features

- **Interactive TUI** - Browse and compare datasets in a terminal interface
- **Side-by-Side Comparison** - Compare two datasets or original vs. processed records
- **Multi-Format Support** - Load JSONL, JSON, Parquet, and CSV with automatic detection
- **Dynamic Schema Detection** - Automatically detects message, ID, and tool fields
- **Dataset Mixer** - Opinionated pipeline that combines specific HuggingFace datasets into a single unified Parquet training file (see [Dataset Mixer](#dataset-mixer) below)
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
# Open a single file (read-only view)
uv run python -m scripts.tui.app dataset/conversations.jsonl

# Open with export mode (original vs. parsed side-by-side)
uv run python -m scripts.tui.app dataset/conversations.jsonl -x

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

### Mix datasets into unified training data

```bash
# Mix all datasets/ into a single Parquet file
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/full_mix_all_sources.parquet

# Nemotron Terminal Corpus only (adapters + synthetic tasks)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/nemotron_terminal_corpus_only.parquet \
  --include Nemotron-Terminal-Corpus

# Everything except Nemotron (TeichAI + Raiden)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/teichai_raiden_no_nemotron.parquet \
  --exclude Nemotron-Terminal-Corpus

# Nemotron-SFT-Agentic-v2 only (search + tool_calling combined)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/nemotron_agentic_v2_combined.parquet \
  --include Nemotron-SFT-Agentic-v2

# Nemotron-SFT-Agentic-v2 with random sample (50%)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/nemotron_agentic_v2_sample_50.parquet \
  --include Nemotron-SFT-Agentic-v2 \
  --sample-rate 0.5

# Nemotron-SFT-Agentic-v2 with random sample (20%) and seed for reproducibility
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/nemotron_agentic_v2_sample_20.parquet \
  --include Nemotron-SFT-Agentic-v2 \
  --sample-rate 0.2 \
  --sample-seed 42

# Dry-run — show record counts per source, no output written
uv run python -m scripts.dataset_mixer datasets/ --dry-run
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
| `q` | Quit |
| `m` | Show field detail modal (global — works on any tree view) |
| `j/k` or `↑/↓` | Move up/down |
| `g/G` | Jump to top/bottom |
| `Enter` | Select item / Expand node |
| `ESC` / `b` | Go back |
| `h/l` or `Tab` | Switch pane focus (dual-pane modes) |
| `e/c` | Expand/collapse all nodes (tree views) |
| `n/p` | Next/previous page (large files) |
| `P/X/x` | Export files/records/record (requires `-x` mode) |

### Parser Finale Formats

| Format | Description |
|--------|-------------|
| `json` | Pretty-printed JSON (default) |
| `jsonl` | One record per line |
| `parquet` | Apache Parquet columnar format |
| `markdown` | Human-readable format |
| `text` | Plain text summary |

## Dataset Mixer

The Dataset Mixer is an **opinionated pipeline** built specifically to combine these HuggingFace datasets into a single unified Parquet training file:

| Dataset | Format | Description |
|---------|--------|-------------|
| [nvidia/Nemotron-Terminal-Corpus](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus) | Parquet | Multi-turn terminal conversations (code, math, SWE, synthetic tasks) |
| [TeichAI/deepseek-v3.2-speciale-openr1-math-3k](https://huggingface.co/datasets/TeichAI/deepseek-v3.2-speciale-openr1-math-3k) | JSONL | Single-turn math reasoning with `<think>` chains |
| [sequelbox/Raiden-Mini-DeepSeek-V3.2-Speciale](https://huggingface.co/datasets/sequelbox/Raiden-Mini-DeepSeek-V3.2-Speciale) | CSV | Creative/analytic reasoning prompt-completion pairs |

Each dataset has a dedicated adapter that handles its specific schema and normalizes records into a unified `conversations`-based output format with metadata columns. The `source_dataset` column tracks which HuggingFace dataset each record originated from (derived from the subdirectory name under `datasets/`).

Place datasets in `datasets/` using their HuggingFace repository name as the directory:
```
datasets/
├── Nemotron-Terminal-Corpus/
├── deepseek-v3.2-speciale-openr1-math-3k/
└── Raiden-Mini-DeepSeek-V3.2-Speciale/
```

### Source Filtering

Use `--include` and `--exclude` to produce filtered mix outputs from a single `datasets/` directory. Filter values are subdirectory names (which become the `source_dataset` column in the output):

```bash
# All data combined (~379,771 records)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/full_mix_all_sources.parquet

# Nemotron only — both dataset_adapters/ and synthetic_tasks/ (~368,413 records)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/nemotron_terminal_corpus_only.parquet \
  --include Nemotron-Terminal-Corpus

# Everything except Nemotron — TeichAI + Raiden (~11,358 records)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/teichai_raiden_no_nemotron.parquet \
  --exclude Nemotron-Terminal-Corpus
```

Filtering operates on the **file list before any data is read** — excluded sources are never opened. Both flags accept multiple values and can be combined (`--include` narrows first, `--exclude` removes from the result).

## Future Plans

The tool is currently optimized for AI conversation datasets but is designed to become a **general-purpose dataset comparer**:

- **Configurable schema detection** - Support any JSON structure, not just conversations
- **ID-based record matching** - Match records by key field instead of index
- **Pluggable transformations** - Optional processing instead of hardcoded parser_finale
- **Additional formats** - Excel/XLSX support

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Architecture Overview](docs/architecture.md) - System design and components
- [Record Structure](docs/record-structure.md) - JSONL data format reference
- [CLI Reference](docs/cli.md) - Complete CLI command documentation
- [TUI Guide](docs/tui.md) - Interactive terminal UI guide
- [Parser Finale](docs/parser-finale.md) - Transformation tool documentation
- [Data Splitter](docs/data-splitter.md) - Dataset splitting utility
- [Data Formats](docs/data-formats.md) - Multi-format loading and schema normalization
- [Verify Datasets](docs/verify-datasets.md) - How to verify mixed training outputs against source datasets

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
│   │   ├── csv_loader.py
│   │   ├── jsonl_loader.py
│   │   ├── json_loader.py
│   │   ├── parquet_loader.py
│   │   ├── format_detector.py
│   │   ├── schema_normalizer.py
│   │   └── directory_loader.py
│   ├── dataset_mixer/    # Opinionated dataset mixing pipeline
│   │   ├── __main__.py   # Entry point (python -m scripts.dataset_mixer)
│   │   ├── cli.py        # CLI: argparse definition
│   │   ├── mixer.py      # Core mixing logic
│   │   ├── adapters.py   # Per-source adapters + auto-detection
│   │   └── schema.py     # Explicit PyArrow output schema
│   └── tui/              # Terminal UI
│       ├── app.py        # Main application
│       ├── keybindings.py # Centralized keybinding definitions
│       ├── data_loader.py
│       ├── views/        # Screen components (record_detail, record_list, comparison, etc.)
│       ├── mixins/       # Reusable behavior (vim nav, dual pane, export, etc.)
│       └── widgets/      # Reusable UI widgets
├── tests/                # Test suite
├── datasets/             # HuggingFace datasets (gitignored)
├── docs/                 # Documentation
└── plans/                # Design plans
```

## License

MIT License - see [LICENSE](LICENSE) for details.
