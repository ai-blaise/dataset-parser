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

## Discovered Issues

### BLOCKER: PyArrow cannot read Nemotron Parquet files with nested columns

@claude-opus-4.6: PyArrow 23.0.0 throws `ArrowNotImplementedError: Nested data conversions not implemented for chunked array outputs` when reading any Parquet file containing the `conversations: list<struct<content: string, role: string>>` column. This affects:

- `ParquetLoader.load()` — uses `iter_batches()` which fails on nested structs
- `ParquetFile.read_row_group()` — also fails
- `pq.read_table()` — also fails
- `pyarrow.dataset` API — also fails

**What works:**
- Reading flat columns individually (e.g. `read_row_group(0, columns=['agent'])`) — OK
- Reading schema metadata (`pq.read_schema()`) — OK, no data read needed

**Root cause:** The Nemotron Parquet files include HuggingFace metadata in the schema (`huggingface: '{"info": {"features": ...}}'`) which may interact with PyArrow's type coercion for nested types in chunked output paths.

**Impact:** Blocks all Nemotron reading (Sources A & B — 368K+ rows, the vast majority of the dataset).

**Potential fixes to investigate:**
1. Upgrade/downgrade PyArrow to a version that handles this
2. Use `pandas.read_parquet()` which uses a different internal code path
3. Use the HuggingFace `datasets` library to load, then convert to Arrow
4. Read flat columns separately and reconstruct the nested column from raw Parquet column data
5. Strip HuggingFace metadata from schema before reading

### ACTION REQUIRED: Add missing dependencies to pyproject.toml

@claude-opus-4.6: Depending on which fix is chosen for the PyArrow nested column issue, new packages may need to be added. Current dependencies (`pyproject.toml`):
- `pyarrow>=15.0.0` (already present — currently at 23.0.0)
- `huggingface-hub>=1.3.2` (already present)

**Packages that may be needed:**
- `pandas` — if fix #2 is chosen (pandas read_parquet uses a different code path)
- `datasets` (HuggingFace) — if fix #3 is chosen (the `datasets` library handles HuggingFace Parquet natively)
- Neither — if fix #1, #4, or #5 works

**Step:** After choosing a fix, run `uv add <package>` to add the dependency and `uv sync` to update the lockfile.

### FIX APPLIED: detect_adapter uses schema metadata instead of loading records

@claude-opus-4.6: Changed `detect_adapter()` to use `pq.read_schema(filename)` for Parquet files instead of loading the first record via `ParquetLoader.load()`. Schema reads work fine — the issue is only with data reads of nested columns.

## Status

| Phase | Status |
|-------|--------|
| Phase 1a (CSV Loader) | DONE |
| Phase 1b (Core Mixer + Adapters) | DONE (PyArrow blocker resolved — `batch_size=1024` fix in `parquet_loader.py`) |
| Phase 2 (CLI) | DONE |
| Phase 3 (Validation) | DONE |
| Phase 4 (Testing) | DONE (45 tests passing — 24 Nemotron parametrized + 6 JSONL + 6 CSV + 6 mix + 3 edge cases) |
| Phase 5 (Source Filtering) | DONE (15 tests passing — 8 unit + 7 integration) |

---

## Phase 4: Testing (pytest)

@claude-opus-4.6: All phases are implemented and the pipeline runs end-to-end. The critical gap is **automated testing** — specifically verifying that conversations pass through each adapter without any modification to user/assistant message content. The test pattern should follow `tests/test_content_integrity.py` (class-based, `copy.deepcopy()` comparisons, `pytest.skip()` for missing data).

### Test file: `tests/test_dataset_mixer.py`

@claude-opus-4.6: All tests below should live in a single file. Tests use **real dataset files** from `datasets/` with `pytest.skip()` when files aren't present, following the pattern in `tests/test_content_integrity.py:L407-L413`.

### 4.1 — Conversation Integrity Per Adapter

@claude-opus-4.6: The core invariant: **adapters must not modify, correct, or reformat the content of any user or assistant message.** Each adapter transforms the *wrapping* (column names, schema shape) but the inner `{"role": "...", "content": "..."}` dicts must be byte-for-byte identical to the source data.

#### `TestNemotronAdapterIntegrity`

@claude-opus-4.6: Nemotron data already has `conversations` in the correct format. The adapter drops `trial_name`/`source` and adds `source_dataset`, but `conversations` must pass through untouched. **Important:** The implementation discovers and processes **29 Parquet files** across 4 categories — tests must sample from each category, not just `code.parquet`.

**Test files (one representative per category):**
- `dataset_adapters/code.parquet` — has extra `source` column (unique to this file)
- `synthetic_tasks/skill_based/easy/debugging/data_filtered.parquet` — easy difficulty
- `synthetic_tasks/skill_based/medium/data_science/data_filtered.parquet` — medium difficulty
- `synthetic_tasks/skill_based/mixed/security/data_filtered.parquet` — mixed difficulty

Tests should use `@pytest.mark.parametrize` over these 4 files so each test runs against all categories.

1. **`test_conversations_unchanged`** — For each of the 4 files, load first N records (e.g. 50) directly via `ParquetLoader`, then load same records via `NemotronAdapter.stream()`. Assert `adapter_record["conversations"] == raw_record["conversations"]` for every record. This catches any accidental transformation, encoding change, or field reordering.

2. **`test_message_content_not_modified`** — For each record across all 4 files, iterate every message in `conversations` and assert `msg["content"]` is identical between raw and adapted. Catches subtle content modifications (whitespace stripping, encoding normalization, etc.).

3. **`test_message_roles_preserved`** — Assert that role values (`"user"`, `"assistant"`, `"system"`) are preserved exactly — no case changes, no renaming.

4. **`test_conversation_length_preserved`** — Assert `len(adapter_conversations) == len(raw_conversations)` — no messages dropped or duplicated.

5. **`test_metadata_columns_present`** — Assert all `OUTPUT_SCHEMA` field names exist as keys in the adapted record.

6. **`test_dropped_columns_absent`** — Assert `trial_name` and `source` are NOT in the adapted record.

#### `TestMessagesJSONLAdapterIntegrity`

@claude-opus-4.6: JSONL source has `messages` key. The adapter renames it to `conversations` — but the inner list of `{"role", "content"}` dicts must be identical.

1. **`test_conversations_match_messages`** — Load first N records from the JSONL via `JSONLLoader`, then via `MessagesJSONLAdapter.stream()`. Assert `adapter_record["conversations"] == raw_record["messages"]` — exact same list, just under a different key name.

2. **`test_user_content_not_modified`** — For each record, find every `role=="user"` message and assert content is identical between raw and adapted.

3. **`test_assistant_content_not_modified`** — Same for `role=="assistant"`. This is the critical one — the parser_finale tool strips assistant content, but the **mixer must NOT**. Assert content includes `<think>` blocks when present in the source.

4. **`test_system_content_not_modified`** — Same for `role=="system"`. The TeichAI data has empty system prompts — verify they stay as empty strings, not `None`.

5. **`test_think_blocks_preserved`** — Explicitly check that assistant messages containing `<think>...</think>` reasoning chains are preserved verbatim. The mixer must not strip, parse, or modify thinking blocks.

6. **`test_conversation_count_preserved`** — Assert number of messages per conversation is identical.

#### `TestPromptCompletionCSVAdapterIntegrity`

@claude-opus-4.6: CSV source has flat `prompt`/`completion` columns. The adapter constructs `[{"role": "user", "content": prompt}, {"role": "assistant", "content": completion}]`. The invariant is: **prompt content becomes user content verbatim, completion content becomes assistant content verbatim.**

1. **`test_prompt_becomes_user_content_verbatim`** — Load first N records from the CSV via `CSVLoader`, then via `PromptCompletionCSVAdapter.stream()`. Assert `adapter_record["conversations"][0]["content"] == raw_record["prompt"]` — exact match, no trimming, no encoding change.

2. **`test_completion_becomes_assistant_content_verbatim`** — Assert `adapter_record["conversations"][1]["content"] == raw_record["completion"]` — exact match. This catches any whitespace stripping, line ending normalization (`\r\n` → `\n`), or truncation.

3. **`test_roles_are_user_then_assistant`** — Assert `conversations[0]["role"] == "user"` and `conversations[1]["role"] == "assistant"`.

4. **`test_conversation_is_exactly_two_messages`** — Assert `len(conversations) == 2` for every CSV record.

5. **`test_large_completion_preserved`** — Find a record with completion > 50K chars (Raiden has completions up to 124K). Assert the full content is preserved — no truncation.

6. **`test_think_blocks_in_completion_preserved`** — All 8,041 Raiden completions contain `<think>` blocks. Assert they survive the adapter.

### 4.2 — End-to-End Mix Integrity

@claude-opus-4.6: After verifying each adapter individually, test the full pipeline: mix → write Parquet → read back → verify conversations match source.

#### `TestMixOutputIntegrity`

1. **`test_mix_subset_conversations_match_sources`** — Create a temp directory with symlinks to one small Parquet, the JSONL, and one CSV. Run `mix()`. Read the output Parquet back. For each `source_dataset`, sample records and verify conversations match the originals.

2. **`test_output_schema_matches`** — Assert the output Parquet schema exactly matches `OUTPUT_SCHEMA` from `schema.py`.

3. **`test_record_count_equals_sum_of_inputs`** — Assert `output_rows == sum(input_counts)`.

4. **`test_source_dataset_values_correct`** — Assert every record has a non-null `source_dataset` and the set of distinct values matches the subdirectory names.

5. **`test_no_empty_conversations`** — Assert no record has `conversations == []` or `conversations == None`.

6. **`test_round_trip_parquet_preserves_conversations`** — Write mixed output, read it back via `ParquetLoader`, verify conversations are still valid `[{"role": "...", "content": "..."}]` structure (catches PyArrow serialization issues with nested structs).

### 4.3 — Negative / Edge Cases

@claude-opus-4.6: Tests that verify the pipeline handles edge cases without silently corrupting data.

1. **`test_comparative_csv_empty_completion`** — `Raiden_Mini_Comparative.csv` has columns `v3.2_speciale_completion`/`v3.2_completion` instead of `completion`. The adapter falls back to `record.get("completion", "")` which produces empty assistant content. Test should verify this behavior is at least consistent (empty string, not `None` or crash).

2. **`test_empty_system_prompt_not_dropped`** — TeichAI data has `{"role": "system", "content": ""}`. Verify this message is kept in the conversation — not filtered out.

3. **`test_unicode_content_preserved`** — If any source has non-ASCII content, verify it survives the adapter + Parquet round-trip.

---

## Phase 5: Source Filtering (`--include` / `--exclude`)

@architect: Need three separate mixed outputs from one `datasets/` directory:
1. **All data combined** — all sources, no filter
2. **Nemotron-only** — just `Nemotron-Terminal-Corpus` (includes both `dataset_adapters/` AND `synthetic_tasks/`)
3. **Non-Nemotron** — everything except `Nemotron-Terminal-Corpus` (TeichAI + Raiden)

@claude-opus-4.6: The `source_dataset` value for all Nemotron files — both `dataset_adapters/` (code, math, swe Parquet) and `synthetic_tasks/` (skill-based Parquet) — is `Nemotron-Terminal-Corpus`, because `discover_files()` derives `source_dataset` from the **first subdirectory** under root (`mixer.py:L43`). So `--include Nemotron-Terminal-Corpus` captures both adapters and synthetic tasks in a single filter.

### 5.1 — Implementation

#### `mixer.py`

Add `_filter_files()` helper and thread `include`/`exclude` through `stream_all()` and `mix()`:

```python
def _filter_files(
  file_list: list[dict[str, str]],
  include: list[str] | None = None,
  exclude: list[str] | None = None,
) -> list[dict[str, str]]:
  """Filter file list by source_dataset name."""
  if include is not None:
    include_set = frozenset(include)
    file_list = [f for f in file_list if f["source_dataset"] in include_set]
  if exclude is not None:
    exclude_set = frozenset(exclude)
    file_list = [f for f in file_list if f["source_dataset"] not in exclude_set]
  return file_list
```

- `stream_all()` gains `include`/`exclude` params, applies `_filter_files()` after discovery
- `mix()` gains `include`/`exclude` params, passes them to `stream_all()`

#### `cli.py`

Add two argparse arguments:

```python
parser.add_argument(
  "--include", nargs="*", default=None,
  help="Only include these source_dataset names (subdirectory names under input_dir)",
)
parser.add_argument(
  "--exclude", nargs="*", default=None,
  help="Exclude these source_dataset names from the mix",
)
```

Pass to `mix()`.

### 5.2 — Usage

```bash
# All data combined (~379,771 records)
uv run python -m scripts.dataset_mixer datasets/ -o all_mixed.parquet

# Nemotron only — adapters + synthetic tasks (~368,413 records)
uv run python -m scripts.dataset_mixer datasets/ -o nemotron_mix.parquet \
  --include Nemotron-Terminal-Corpus

# Non-Nemotron — TeichAI + Raiden (~11,358 records)
uv run python -m scripts.dataset_mixer datasets/ -o non_nemotron_mix.parquet \
  --exclude Nemotron-Terminal-Corpus

# Multiple includes (if more sources added later)
uv run python -m scripts.dataset_mixer datasets/ -o subset.parquet \
  --include Nemotron-Terminal-Corpus Raiden-Mini-DeepSeek-V3.2-Speciale
```

### 5.3 — Behavior

- `--include` and `--exclude` can be used together: include narrows first, exclude removes from that result
- If `--include` names a nonexistent source, result is 0 records (no crash, empty output skipped)
- If neither flag is set, all sources are processed (current behavior, no regression)
- Filtering happens on the file list **before** any adapters run — zero overhead

### 5.4 — Tests (`tests/test_dataset_mixer.py`)

Add to the existing test file following the same patterns (real data with `pytest.skip()`).

#### `TestSourceFiltering`

1. **`test_include_single_source`** — Run `mix()` with `include=["Nemotron-Terminal-Corpus"]`. Assert every record in output has `source_dataset == "Nemotron-Terminal-Corpus"`. Assert record count matches sum of all Nemotron files (adapters + synthetic).

2. **`test_include_nemotron_gets_both_adapters_and_synthetic`** — Run `mix()` with `include=["Nemotron-Terminal-Corpus"]`. Discover files separately and verify that both `dataset_adapters/` and `synthetic_tasks/` files are present in the filtered list. This confirms that one `--include` value captures all 29 Nemotron Parquet files.

3. **`test_exclude_single_source`** — Run `mix()` with `exclude=["Nemotron-Terminal-Corpus"]`. Assert no record in output has `source_dataset == "Nemotron-Terminal-Corpus"`. Assert the remaining sources are `deepseek-v3.2-speciale-openr1-math-3k` and `Raiden-Mini-DeepSeek-V3.2-Speciale`.

4. **`test_exclude_record_count_matches_non_nemotron`** — Run `mix()` with `exclude=["Nemotron-Terminal-Corpus"]`. Assert record count equals sum of TeichAI (3,317) + Raiden (8,041) records.

5. **`test_no_filter_includes_all_sources`** — Run `mix()` with no `include`/`exclude`. Assert output contains records from all three `source_dataset` values. Confirms no regression.

6. **`test_include_nonexistent_source_returns_zero`** — Run `mix()` with `include=["does-not-exist"]`. Assert `total_records == 0` and no output file is written.

7. **`test_include_and_exclude_compose`** — Run `mix()` with `include=["Nemotron-Terminal-Corpus", "Raiden-Mini-DeepSeek-V3.2-Speciale"]` and `exclude=["Raiden-Mini-DeepSeek-V3.2-Speciale"]`. Assert output contains only Nemotron records.

8. **`test_filter_files_unit`** — Unit test `_filter_files()` directly with a synthetic file list. Test include-only, exclude-only, both, and neither.

---

## Post-Implementation Updates

@architect: The mixer was crashing on CSV files without prompt/completion columns — it needs to validate columns. Also the TUI viewer must work with mixed Parquet output (which uses `conversations` not `messages`), so parser_finale needs to handle both key names. Default normalization in the data loader should be off so the TUI shows raw field names as they exist in the data. The record list columns should show actual field names, not hardcoded IDX/ID/MSGS/TOOLS/PREVIEW. Added a read-only view mode with `-x`/`--export` flag. Keybindings must be a GLOBAL setting that ALL views obey — they were scattered with inconsistencies. The `m` key for the detail modal must work everywhere a JsonTreePanel is visible. The modal was crashing on data with `[`, `]`, `=` characters. Added verify-datasets documentation.

@claude-opus-4.6: Hardened mixer, added conversations key support, disabled default normalization, centralized keybindings, global `m` binding, field-driven columns, read-only view mode, and fixed modal crash.

Dataset mixer hardening:
- `scripts/dataset_mixer/adapters.py`: `detect_adapter()` for CSV now validates `prompt`/`completion` columns exist in the first record; raises ValueError with column names on mismatch
- `scripts/dataset_mixer/mixer.py`: `stream_all()` wraps `detect_adapter()` in try/except ValueError and skips unrecognized files instead of crashing the entire mix

Conversations key support & normalization:
- `scripts/parser_finale.py`: `process_record()` now supports both `messages` (JSONL) and `conversations` (Parquet) keys — checks for `conversations` first, falls back to `messages`
- `scripts/tui/data_loader.py`: `normalize` default changed from `True` to `False` in `load_records()`, `load_all_records()`, `load_records_range()`, and `load_record_at_index()` — TUI shows raw field names
- `tests/test_multiformat_tui.py`: updated all assertions to expect raw column names (`conversations` for Parquet, `messages` for JSONL/JSON) instead of assuming normalization

Read-only view mode:
- `scripts/tui/views/record_detail.py`: new screen — full-width single-pane JsonTreePanel, no parser_finale processing
- `scripts/tui/app.py`: added `export_mode` flag and `-x`/`--export` CLI arg; `show_comparison()` routes to RecordDetailScreen (default) or ComparisonScreen (`-x`)
- `scripts/tui/views/__init__.py`: exported RecordDetailScreen

Centralized keybindings:
- Created `scripts/tui/keybindings.py`: single source of truth for all binding groups (GLOBAL, BACK, VIM_NAV, PANEL, TREE, PAGE, MODAL) plus composites (SINGLE_PANE_BINDINGS, DUAL_PANE_BINDINGS)
- All views updated to import from keybindings module instead of defining inline
- `scripts/tui/mixins/dual_pane.py`: re-exports from keybindings; renamed `action_show_field_detail` → `action_show_detail`
- `scripts/tui/mixins/vim_navigation.py`: re-exports VIM_NAV_BINDINGS
- Fixed: FileListScreen escape→quit changed to escape→go_back; added action_go_back
- Fixed: RecordDetailScreen was missing j/k vim navigation bindings

Global `m` binding:
- `m` → `show_detail` moved to GLOBAL_BINDINGS (available on every screen)
- `scripts/tui/app.py`: app-level `action_show_detail` finds any visible JsonTreePanel and calls `emit_node_selected()`; app-level `on_json_tree_panel_node_selected` as fallback handler
- `scripts/tui/views/record_detail.py`: fixed action_show_detail — was checking `node.data` (Textual's generic string) instead of using `tree.emit_node_selected()`

Field-driven record list columns (diverges from generalize-data-table-format plan):
- `scripts/tui/mixins/record_table.py`: `_get_record_columns` now derives columns from actual top-level field names of records instead of hardcoded IDX/ID/MSGS/TOOLS/PREVIEW; added `_detect_field_columns()`, `_preview_value()`
- API changed: `_get_record_columns(mapping)` → `_get_record_columns(mapping, records=...)`; `_build_record_row(summary, mapping)` → `_build_record_row(summary, mapping, record=...)`

Modal crash fix:
- `scripts/tui/widgets/field_detail_modal.py`: added `markup=False` to Static widget — data with `[`, `]`, `=` chars caused MarkupError crash; uses MODAL_BINDINGS from keybindings module

Documentation:
- `docs/verify-datasets.md`: new doc on verifying mixed training outputs against source datasets
- `README.md`: added link to verify-datasets doc
