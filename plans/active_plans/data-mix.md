# Plan: dataset-mixer — Dataset Mixing Pipeline

## Problem

We have multiple datasets in `datasets/` with varying formats and schemas that need to be combined into a single unified Parquet training dataset. Currently there is no tool to mix these together while tracking which dataset each record originated from.

## Goal

Build `dataset-mixer`, a pipeline that:
1. Ingests all dataset files from `datasets/` (Parquet, JSONL, CSV)
2. Transforms each source's conversation data into a unified `conversations` column
3. Fills metadata columns (from source data where available, defaults/nulls where not)
4. Adds `source_dataset` — provenance tracking for each record's origin
5. Outputs a single consolidated Parquet file ready for training

@architect: Name should be `dataset-mixer` (not `data-synt`).

## Unified Output Schema

@claude-opus-4.6: Schema is based on the Nemotron Terminal Corpus `dataset_adapters` format — one conversation per row. All conversation data lives in the `conversations` column as `[{"role": "...", "content": "..."}]`. Verified that this structure is identical across all source datasets.

| Column | Type | Description |
|--------|------|-------------|
| `conversations` | `list<struct<content: string, role: string>>` | Full conversation. One row = one complete conversation. |
| `agent` | `string` | Agent system/identity that generated the data |
| `model` | `string` | LLM used to generate assistant responses |
| `model_provider` | `string` | API provider (e.g. `hosted_vllm`, `anthropic`) |
| `date` | `string` | Timestamp of conversation generation |
| `task` | `string` | Task/scenario identifier |
| `episode` | `string` | Grouping of related runs |
| `run_id` | `string` | Batch/session identifier |
| `enable_thinking` | `bool` | Whether extended thinking was enabled |
| `source_dataset` | `string` | **Origin dataset** — which dataset this record came from |

### Dropped columns (Nemotron-specific)
- `trial_name` — replaced by `source_dataset` for cross-dataset provenance
- `source` — only exists in `code.parquet` (values: `"OpenCodeReasoning"`, `"synthetic"`); not part of unified schema

### Resolved decisions
- Output format: **Parquet** (@architect)
- No `difficulty` column (@architect)
- No `skill` column (@architect)
- No additional columns beyond the schema above (@architect)
- `source_dataset` replaces `trial_name` as the provenance column (@architect)

### Open questions for @architect
- What should the `source_dataset` values be per source? (e.g. per-file labels, per-corpus labels, etc.)

@architect: It should be the name of the dataset it came from.

---

## Source Inventory & Verified Schemas

@claude-opus-4.6: All sources inspected and schemas verified. Core finding: **every dataset stores conversations as `[{"role": "...", "content": "..."}]` dicts** — they just package them differently. The conversation format is identical across all sources; only the wrapping differs.

### Source A: Nemotron Terminal Corpus — `dataset_adapters/` (Parquet)

@claude-opus-4.6: These are NOT raw datasets. NVIDIA **adapted** pre-existing datasets (OpenCodeReasoning, math benchmarks, SWE-bench) by replaying original problems through their `terminus-2` agent with DeepSeek-V3.2 to generate multi-turn terminal conversation trajectories. The `dataset_adapters` name means "we adapted these datasets into our format." All metadata is constant across all rows: `agent="terminus-2"`, `model="deepseek-ai/DeepSeek-V3.2"`, `model_provider="hosted_vllm"`, `enable_thinking=true`.

| File | Rows | Original Source |
|------|------|----------------|
| `code.parquet` | 31,960 | OpenCodeReasoning + synthetic |
| `math.parquet` | 162,692 | Math benchmarks |
| `swe.parquet` | 31,661 | SWE-bench style GitHub issues |

**Schema**: Already matches the unified output schema exactly.
```
conversations: list<struct<content: string, role: string>>
agent: "terminus-2"  (constant across all rows)
model: "deepseek-ai/DeepSeek-V3.2"  (constant)
model_provider: "hosted_vllm"  (constant)
date: string
task: string
episode: string
run_id: string
trial_name: string  (to be dropped)
enable_thinking: true  (constant)
```
Extra column: `source` in `code.parquet` only (values: `"OpenCodeReasoning"`, `"synthetic"` — to be dropped).

**Transform**: Trivial — drop `trial_name` + `source`, add `source_dataset`.

### Source B: Nemotron Terminal Corpus — `synthetic_tasks/` (Parquet)

@claude-opus-4.6: Generated from NVIDIA's terminal skill taxonomy. Same agent, same model, same schema as Source A. Initially appeared to have a flat `content`/`role` schema but verified that those are child fields of the `conversations` list struct — the actual schema is identical to the adapters.

| Difficulty | Skills | Total Rows |
|-----------|--------|------------|
| easy | 9 skills | ~44,800 |
| medium | 11 skills | ~91,600 |
| mixed | 6 skills | ~5,700 |

**Schema**: Identical to Source A (verified).

**Transform**: Same as Source A — drop `trial_name`, add `source_dataset`.

### Source C: TeichAI `deepseek-v3.2-speciale-openr1-math-3k` (JSONL)

@architect: This dataset has entries in the conversational format we care about. Verified to be similar to Nemotron where there is a column that includes the conversation data.

@claude-opus-4.6: Single-turn math reasoning responses. Only column is `messages` — no metadata at all. Conversation structure verified identical to Nemotron: each message has exactly `{"role", "content"}` keys.

| Detail | Value |
|--------|-------|
| Rows | 3,317 |
| Format | JSONL |
| Columns | `messages` only — no metadata |

**Conversation structure** (verified):
```
messages: [
  {"role": "system", "content": ""},      # empty system prompt
  {"role": "user", "content": "..."},      # math problem
  {"role": "assistant", "content": "..."}  # response with <think> reasoning
]
```

**Transform**:
- Rename `messages` → `conversations`
- Fill metadata columns with defaults: `model` = `"deepseek-ai/DeepSeek-V3.2"` (known from dataset name), others = `null`
- `enable_thinking` = `true` (all responses contain `<think>` blocks)
- Add `source_dataset`

### Source D: sequelbox `Raiden-Mini-DeepSeek-V3.2-Speciale` (CSV)

@architect: Creative-reasoning and analytic-reasoning responses testing DeepSeek-V3.2.Speciale's reasoning skills. Should also be in conversation format in the unified dataset.

@claude-opus-4.6: Flat prompt/completion pair format — not conversational, but trivially convertible. All 8,041 completions contain `<think>` reasoning chains. Completions can be very large (up to 124K chars).

| Detail | Value |
|--------|-------|
| Rows | 8,041 |
| Format | CSV |
| Columns | `prompt`, `completion` — no metadata |
| Completions | All 8,041 contain `<think>` reasoning chains |
| Content size | Completions up to 124K chars (extended reasoning) |

**Transform**:
- Construct `conversations` list from each row:
  ```
  [{"role": "user", "content": <prompt>}, {"role": "assistant", "content": <completion>}]
  ```
- Fill metadata: `model` = `"deepseek-ai/DeepSeek-V3.2"` (known), others = `null`
- `enable_thinking` = `true` (all completions have `<think>` blocks)
- Add `source_dataset`

---

## Conversation Format Compatibility (Verified)

@claude-opus-4.6: All sources produce the same inner structure — `[{"role": "...", "content": "..."}]`. Verified by parsing actual entries from each source in this session.

| Source | Storage Format | Conversation Key | Message Keys | Transform |
|--------|---------------|-----------------|--------------|-----------|
| Nemotron adapters | Parquet list column | `conversations` | `{role, content}` | Drop `trial_name`/`source`, add `source_dataset` |
| Nemotron synthetic | Parquet list column | `conversations` | `{role, content}` | Same as above |
| TeichAI math-3k | JSONL | `messages` | `{role, content}` | Rename key, fill metadata |
| Raiden Speciale | CSV | `prompt` + `completion` | N/A (flat) | Construct list from pair, fill metadata |

---

## Existing Infrastructure (Reuse Audit)

@claude-opus-4.6: Audited the full codebase. The `scripts/data_formats/` module provides a production-ready loader framework that the mixer should build on — not duplicate. Key components:

### What already exists

| Component | Location | Reuse in Mixer |
|-----------|----------|----------------|
| `DataLoader` ABC | `scripts/data_formats/base.py` | Base class for the new `CSVLoader`. Defines `load()`, `load_all()`, `get_record_count()`, `get_record_at_index()`. |
| Format auto-detection | `scripts/data_formats/format_detector.py` | `EXTENSION_MAP` and `get_loader()` factory. Add `.csv` → `"csv"` to extend. |
| Directory discovery | `scripts/data_formats/directory_loader.py` | `discover_data_files()` already scans dirs. Derives `SUPPORTED_EXTENSIONS` from `EXTENSION_MAP` — adding CSV propagates automatically. |
| Parquet loader | `scripts/data_formats/parquet_loader.py` | Reads Nemotron sources (A, B). Handles nested `conversations` struct → Python dicts via `_convert_nested_to_python()`. |
| JSONL loader | `scripts/data_formats/jsonl_loader.py` | Reads TeichAI source (C). Streams line-by-line, O(1) memory. |
| Schema normalizer | `scripts/data_formats/schema_normalizer.py` | Current direction is `conversations` → `messages` (for TUI's standard). Mixer needs the **reverse**: `messages` → `conversations`. See normalization strategy below. |
| Parquet writer | `scripts/parser_finale.py:write_parquet()` | `pa.Table.from_pylist(records)` → `pq.write_table()`. Can reuse for output, but mixer should define an explicit PyArrow schema rather than relying on inference. |
| TUI comparison | `scripts/tui/app.py` | `--compare` mode can visually QA pre-mix vs post-mix datasets. |

### What needs to be built

1. **`CSVLoader`** — New `DataLoader` subclass in `scripts/data_formats/csv_loader.py`. Needed for Source D (Raiden Speciale). Uses `csv.DictReader` for streaming. Must handle large fields (completions up to 124K chars).
2. **CSV in format detection** — Add `.csv` → `"csv"` to `EXTENSION_MAP` and `"csv"` to `SUPPORTED_FORMATS` in `format_detector.py`. Wire `CSVLoader` into `get_loader()` and `get_loader_for_format()`.
3. **Mixer-specific normalization** — A new normalization path in `dataset_mixer/adapters.py` that targets `conversations` (Parquet convention) directly, NOT the TUI's `messages` standard. This avoids a pointless `conversations` → `messages` → `conversations` round-trip for Nemotron sources.
4. **Mixer adapters** — Three adapter types (below) that use the existing loaders for I/O but apply mixer-specific transforms.
5. **PyArrow output schema** — Explicit `pa.schema()` definition for the unified output, enforced on write.

### Normalization strategy

@claude-opus-4.6: The existing `schema_normalizer.py` normalizes **toward `messages`** (the TUI's internal standard). The mixer normalizes **toward `conversations`** (the Parquet training output standard). These are two different normalization targets — do NOT modify the existing normalizer. Instead, the mixer adapters handle their own field mapping:

```
Existing normalizer (TUI path):     Parquet conversations → messages
Mixer adapters (training path):     JSONL messages → conversations
                                    CSV prompt/completion → conversations
                                    Parquet conversations → conversations (pass-through)
```

---

## Architecture

```
scripts/
├── data_formats/
│   ├── csv_loader.py     # NEW — CSVLoader (DataLoader subclass)
│   ├── format_detector.py # MODIFY — add .csv to EXTENSION_MAP + SUPPORTED_FORMATS
│   ├── __init__.py        # MODIFY — export CSVLoader
│   └── (existing files unchanged)
└── dataset_mixer/
    ├── __init__.py
    ├── __main__.py       # Entry point — makes `python -m scripts.dataset_mixer` work
    ├── mixer.py          # Core mixing logic — load via data_formats loaders, transform, concat, write
    ├── adapters.py       # Per-source adapters (transform to unified conversations schema)
    └── cli.py            # CLI: argparse definition, specify input dir, source labels, output path
```

### How to run

@claude-opus-4.6: Follows the same `uv run python -m` pattern as all other tools in this project (`parser_finale`, `main`, `tui.app`, `data_splitter`).

```bash
# Mix all datasets/ into a single Parquet file
uv run python -m scripts.dataset_mixer datasets/ -o mixed_output.parquet

# Dry-run — show record counts per source, no output written
uv run python -m scripts.dataset_mixer datasets/ --dry-run

# Custom output path
uv run python -m scripts.dataset_mixer datasets/ -o training/final_mix.parquet
```

`__main__.py` is a thin entry point:
```python
from scripts.dataset_mixer.cli import main
main()
```

### Adapter types needed

@claude-opus-4.6: Three adapter types cover all current sources. Each adapter wraps an existing `DataLoader` for I/O and applies source-specific transforms to produce the unified `conversations`-based schema. Auto-detection picks the right adapter based on file format + column inspection.

1. **NemotronAdapter** — Uses existing `ParquetLoader`. Parquet with `conversations` column + full metadata. Drop `trial_name`/`source`, add `source_dataset`. Pass-through for all other columns.
2. **MessagesJSONLAdapter** — Uses existing `JSONLLoader`. JSONL with `messages` key only. Rename to `conversations`, fill metadata with known defaults or nulls.
3. **PromptCompletionCSVAdapter** — Uses new `CSVLoader`. CSV with `prompt`/`completion` columns. Construct `conversations` list, fill metadata.

---

## Phases

### Phase 1a: CSV Loader (prerequisite)
- Implement `CSVLoader` in `scripts/data_formats/csv_loader.py` following `DataLoader` ABC
- Add `.csv` to `EXTENSION_MAP` and `SUPPORTED_FORMATS` in `format_detector.py`
- Wire into `get_loader()` / `get_loader_for_format()` factory functions
- Export from `scripts/data_formats/__init__.py`
- Handle large fields (Raiden completions up to 124K chars — may need `csv.field_size_limit()`)
- Tests for CSV loading

### Phase 1b: Core Mixer + Adapters
- Define canonical output schema as an explicit `pa.schema()` (not inferred)
- Implement all 3 adapters (Nemotron, MessagesJSONL, PromptCompletionCSV) wrapping existing loaders
- Auto-detect adapter type from file format + column inspection
- Stream-process large files (Nemotron math.parquet is 162K rows — cannot load all into memory)
- Write single output Parquet file with schema enforcement

### Phase 2: CLI
- CLI to specify input directory, output path
- Source label mapping (file/dir → `source_dataset` value)
- Dry-run mode (show record counts per source without writing)

### Phase 3: Validation
- Record count verification (sum of inputs = output rows)
- Schema conformance check on output
- Distribution report (records per `source_dataset`, per `task`)

---

## Total Dataset Size

| Source | Rows |
|--------|------|
| Nemotron adapters (code + math + swe) | 226,313 |
| Nemotron synthetic tasks (easy + medium + mixed) | ~142,100 |
| TeichAI math-3k | 3,317 |
| Raiden Speciale | 8,041 |
| **Grand total** | **~379,771** |

---

## Status

| Phase | Status |
|-------|--------|
| Phase 1 | NOT STARTED |
| Phase 2 | NOT STARTED |
| Phase 3 | NOT STARTED |
