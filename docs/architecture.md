# Architecture Overview

This document describes the architecture of the dataset-parser tool.

## System Overview

dataset-parser is a modular toolkit for exploring and comparing datasets. Currently optimized for AI conversation data, with architecture designed for future generalization to any dataset type.

**Core interfaces:**

1. **TUI Application** - Interactive terminal UI for browsing and comparing datasets
2. **CLI Tool** - Command-line interface for dataset exploration
3. **Parser Finale** - Transformation engine for processing records (AI-specific)
4. **Data Splitter** - Utility for splitting files into N parts

**Key architectural strengths:**
- Pluggable format loaders (JSONL, JSON, Parquet)
- Generic JSON diff engine
- Schema-aware field detection
- Mixin-based UI composition

## Directory Structure

```
dataset-parser/
├── main.py                    # Stub entry point
├── pyproject.toml             # Project metadata and dependencies
├── uv.lock                    # Dependency lock file
├── README.md                  # Quick start guide
├── LICENSE                    # MIT License
├── AGENTS.md                  # Development workflow instructions
│
├── scripts/                   # Main application code
│   ├── main.py                # CLI tool implementation
│   ├── parser_finale.py       # Core record processor (AI-specific)
│   ├── data_splitter.py       # Dataset splitting utility
│   ├── data_formats/          # Multi-format data loaders
│   │   ├── base.py            # Abstract DataLoader class
│   │   ├── jsonl_loader.py    # JSONL format
│   │   ├── json_loader.py     # JSON format
│   │   ├── parquet_loader.py  # Parquet format
│   │   ├── format_detector.py # Auto-detection
│   │   ├── schema_normalizer.py
│   │   └── directory_loader.py
│   └── tui/                   # Terminal UI application
│       ├── app.py             # Main Textual app
│       ├── data_loader.py     # Data loading with schema detection
│       ├── mixins/            # Reusable behavior mixins
│       │   ├── data_table.py      # DataTable utilities
│       │   ├── record_table.py    # Schema-aware record tables
│       │   ├── dual_pane.py       # Dual-pane management
│       │   ├── vim_navigation.py  # j/k/h/l navigation
│       │   ├── export.py          # Export functionality
│       │   └── background_task.py # Async loading
│       ├── views/             # Screen components
│       │   ├── file_list.py
│       │   ├── record_list.py
│       │   ├── comparison_screen.py
│       │   └── dual_record_list_screen.py
│       ├── widgets/           # Reusable UI components
│       │   ├── json_tree_panel.py
│       │   ├── diff_indicator.py
│       │   └── field_detail_modal.py
│       ├── screens/           # Modal screens
│       │   ├── loading_screen.py
│       │   └── exporting_screen.py
│       └── styles/            # CSS styles
│           └── base.tcss
│
├── tests/                     # Test suite
│   ├── conftest.py            # Pytest fixtures
│   ├── test_*.py              # Test modules
│   └── fixtures/              # Test data
│
└── docs/                      # Documentation
```

## Component Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    dataset-parser Application                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┬──────────────┬─────────────┬──────────────────┐ │
│  │  CLI Tool   │Parser Finale │    TUI      │  Data Splitter   │ │
│  │ (main.py)   │(AI-specific) │  (app.py)   │ (data_splitter)  │ │
│  └──────┬──────┴──────┬───────┴──────┬──────┴──────────────────┘ │
│         │             │              │                            │
│         └─────────────┼──────────────┘                            │
│                       │                                           │
│            ┌──────────▼──────────┐                                │
│            │     Data Loader     │   ← Schema Detection           │
│            │   (data_loader.py)  │   ← Field Mapping              │
│            │                     │   ← Record Caching             │
│            └──────────┬──────────┘                                │
│                       │                                           │
│            ┌──────────▼──────────┐                                │
│            │   Format Loaders    │   ← Pluggable Architecture     │
│            │  (data_formats/)    │                                │
│            │  ├── JSONL          │                                │
│            │  ├── JSON           │                                │
│            │  └── Parquet        │                                │
│            └──────────┬──────────┘                                │
│                       │                                           │
│            ┌──────────▼──────────┐                                │
│            │   Dataset Files     │                                │
│            └────────────────────┘                                │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│ TUI Component Hierarchy (Textual Framework)                       │
│                                                                   │
│ JsonComparisonApp                                                 │
│ ├── FileListScreen              (directory browsing)              │
│ ├── RecordListScreen            (record table with schema detect) │
│ │   └── RecordTableMixin → DataTableMixin                         │
│ ├── ComparisonScreen            (original vs processed)           │
│ │   ├── JsonTreePanel           (generic JSON display)            │
│ │   └── DiffIndicator           (generic JSON diff)               │
│ └── DualRecordListScreen        (dataset vs dataset)              │
│     └── Independent pane navigation                               │
└──────────────────────────────────────────────────────────────────┘
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

Shared utilities for loading and processing data with dynamic schema detection:

| Function | Purpose |
|----------|---------|
| `detect_messages_field()` | Find array with message-like objects |
| `detect_uuid_field()` | Find ID field by name or UUID pattern |
| `detect_tools_field()` | Find array with tool definitions |
| `detect_schema()` | Detect full schema mapping for a record |
| `get_field_mapping()` | Get cached schema for a file |
| `load_records()` | Lazy generator supporting all formats |
| `load_all_records()` | Load full file with schema detection |
| `get_record_summary()` | Extract metadata using schema mapping |
| `load_record_pair()` | Return (original, processed) tuple |
| `load_record_pair_comparison()` | Load matching records from two files |

**Schema Detection**: The loader automatically detects field mappings on first record load, caching the schema per-file. This enables dynamic column generation based on actual data structure.

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
