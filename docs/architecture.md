# Architecture Overview

This document describes the architecture of the data-gen JSONL dataset exploration tool.

## System Overview

data-gen is a modular toolkit for exploring and transforming JSONL datasets containing AI conversation data. It provides three main interfaces:

1. **CLI Tool** - Command-line interface for dataset exploration
2. **Parser Finale** - Core transformation engine for processing records
3. **TUI Application** - Interactive terminal UI for browsing datasets
4. **Data Splitter** - Utility for splitting JSONL files into N parts

## Directory Structure

```
data-gen/
├── main.py                    # Stub entry point
├── pyproject.toml             # Project metadata and dependencies
├── uv.lock                    # Dependency lock file
├── README.md                  # Quick start guide
├── LICENSE                    # MIT License
├── AGENTS.md                  # Development workflow instructions
│
├── scripts/                   # Main application code
│   ├── main.py                # CLI tool implementation
│   ├── parser_finale.py       # Core JSONL processor
│   ├── data_splitter.py       # Dataset splitting utility
│   └── tui/                   # Terminal UI application
│       ├── __init__.py
│       ├── app.py             # Main Textual app
│       ├── data_loader.py     # JSONL loading utilities
│       ├── views/             # Screen components
│       │   ├── record_list.py
│       │   └── comparison_screen.py
│       └── widgets/           # Reusable UI components
│           ├── json_tree_panel.py
│           ├── diff_indicator.py
│           └── field_detail_modal.py
│
├── tests/                     # Test suite
│   ├── conftest.py            # Pytest fixtures
│   ├── test_*.py              # Test modules
│   └── fixtures/              # Test data
│       ├── valid/
│       ├── edge_cases/
│       └── invalid/
│
└── docs/                      # Documentation
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  data-gen Application                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────┬─────────────────┬───────────┬───────────────┐  │
│  │   CLI Tool    │  Parser Finale  │   TUI     │ Data Splitter │  │
│  │  (main.py)    │(parser_finale)  │  (app.py) │(data_splitter)│  │
│  └───────┬───────┴────────┬────────┴─────┬─────┴───────────────┘  │
│           │                   │                │        │
│           └───────────────────┼────────────────┘        │
│                               │                         │
│                    ┌──────────▼─────────┐               │
│                    │    Data Loader     │               │
│                    │  (data_loader.py)  │               │
│                    │                    │               │
│                    │  - load_jsonl()    │               │
│                    │  - process_record()│               │
│                    │  - get_summary()   │               │
│                    └──────────┬─────────┘               │
│                               │                         │
│                    ┌──────────▼─────────┐               │
│                    │   JSONL Records    │               │
│                    │  (Dataset files)   │               │
│                    └────────────────────┘               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ TUI Component Hierarchy (Textual Framework)             │
│                                                         │
│ JsonComparisonApp                                       │
│ ├── RecordListScreen                                    │
│ │   └── DataTable (record summaries)                    │
│ └── ComparisonScreen                                    │
│     ├── JsonTreePanel (original record)                 │
│     ├── JsonTreePanel (processed record)                │
│     ├── FieldDetailModal (detail view)                  │
│     └── DiffIndicator (highlighting)                    │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### CLI Tool (`scripts/main.py`)

The CLI provides four commands for dataset exploration:

| Command | Purpose |
|---------|---------|
| `list` | Display tabular summary of records |
| `show` | View individual records or specific fields |
| `search` | Search text across records |
| `stats` | Display dataset statistics |

See [CLI Documentation](cli.md) for detailed usage.

### Parser Finale (`scripts/parser_finale.py`)

The core transformation engine that processes JSONL records by removing assistant message content while preserving the overall structure. This is useful for:

- Extracting training prompts without model responses
- Analyzing input data independently
- Creating filtered datasets

See [Parser Finale Documentation](parser-finale.md) for detailed usage.

### TUI Application (`scripts/tui/`)

An interactive terminal interface built with the [Textual](https://textual.textualize.io/) framework. It provides:

- **Record List View**: Browse all records in a table format
- **Comparison View**: Side-by-side diff of original vs processed records
- **Field Detail Modal**: Detailed view of individual fields

See [TUI Documentation](tui.md) for detailed usage.

### Data Splitter (`scripts/data_splitter.py`)

A standalone utility for splitting JSONL files into N equal (or near-equal) parts. Key features:

- Handles both even and odd record counts
- Streaming implementation for memory efficiency
- Supports dry-run mode for previewing splits
- Includes verification to confirm recombination matches original
- Preserves exact line formatting

See [Data Splitter Documentation](data-splitter.md) for detailed usage.

### Data Loader (`scripts/tui/data_loader.py`)

Shared utilities for loading and processing JSONL data:

| Function | Purpose |
|----------|---------|
| `load_jsonl()` | Lazy generator for memory-efficient loading |
| `load_all_records()` | Load full file into memory |
| `get_record_summary()` | Extract metadata for display |
| `load_record_pair()` | Return (original, processed) tuple |
| `truncate()` | Helper for display truncation |
| `get_record_diff()` | Calculate differences between records |

## Design Principles

### 1. Lazy Loading

JSONL records are loaded on-demand via generators. This enables handling large datasets without consuming excessive memory.

### 2. Separation of Concerns

The CLI, TUI, and parser logic are modular and independent. Each component can be used standalone or combined as needed.

### 3. Parser Finale Pattern

The core transformation empties assistant responses while preserving structure, enabling training data extraction without model outputs.

### 4. Comprehensive Testing

The test suite covers CLI commands, record processing, JSONL loading, output formatting, and edge cases using fixture-based test data.

## Data Flow

1. **Input**: JSONL files containing conversation records
2. **Loading**: Data loader reads records lazily or fully as needed
3. **Processing**: Parser finale transforms records (removes assistant content)
4. **Output**: Results displayed via CLI, TUI, or written to files

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.12+ | Runtime |
| textual | >=7.3.0 | Terminal UI framework |
| pytest | >=9.0.2 | Testing (dev) |

The project uses `uv` for fast, reproducible dependency management.
