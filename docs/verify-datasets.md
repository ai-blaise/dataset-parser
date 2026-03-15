# How to Verify the Datasets

This guide covers how to verify that the mixed training datasets in `output-datasets/` correctly preserve conversation content from the original source datasets.

## Prerequisites

Generate the mixed outputs first:

```bash
# All data combined
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/full_mix_all_sources.parquet

# Nemotron only (adapters + synthetic tasks)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/nemotron_terminal_corpus_only.parquet \
  --include Nemotron-Terminal-Corpus

# TeichAI + Raiden (non-Nemotron)
uv run python -m scripts.dataset_mixer datasets/ -o output-datasets/teichai_raiden_no_nemotron.parquet \
  --exclude Nemotron-Terminal-Corpus
```

## Side-by-Side Comparison (TUI)

Use `--compare` to launch the dual-pane TUI with a source dataset on the left and the mixed output on the right. Both paths must be directories.

### Compare TeichAI source against mixed output

```bash
uv run python -m scripts.tui.app datasets/deepseek-v3.2-speciale-openr1-math-3k/ \
  --compare output-datasets/
```

**What to verify:**
- Each TeichAI record has `messages` (source) mapped to `conversations` (output)
- Assistant content contains `<think>` reasoning chains (not empty)
- System prompts are preserved as empty strings (not dropped)
- Record count: 3,317

### Compare Raiden source against mixed output

```bash
uv run python -m scripts.tui.app datasets/Raiden-Mini-DeepSeek-V3.2-Speciale/ \
  --compare output-datasets/
```

**What to verify:**
- Only `Raiden_Mini_DS3.2_Speciale.csv` is included (8,041 records)
- `Raiden_Mini_Comparative.csv` is excluded (different column schema — no `completion` column)
- Each conversation has exactly 2 messages: user (prompt) + assistant (completion)
- Assistant content contains `<think>` reasoning chains (not empty)
- Large completions (up to 124K chars) are not truncated

### Compare Nemotron source against mixed output

```bash
uv run python -m scripts.tui.app datasets/Nemotron-Terminal-Corpus/ \
  --compare output-datasets/
```

**What to verify:**
- Both `dataset_adapters/` (code, math, swe) and `synthetic_tasks/` files are present
- Conversations pass through unchanged (same structure in source and output)
- Metadata columns (`agent`, `model`, `model_provider`, `task`, etc.) are preserved
- `trial_name` and `source` columns are dropped from the output

## Browse a Single Mixed Output

To inspect a mixed parquet without comparison:

```bash
# Browse the full mix
uv run python -m scripts.tui.app output-datasets/full_mix_all_sources.parquet

# Browse Nemotron-only mix
uv run python -m scripts.tui.app output-datasets/nemotron_terminal_corpus_only.parquet

# Browse TeichAI + Raiden mix
uv run python -m scripts.tui.app output-datasets/teichai_raiden_no_nemotron.parquet
```

## TUI Keybindings (Comparison Mode)

| Key | Action |
|-----|--------|
| `Tab` | Switch between left and right panes |
| `h` / `l` | Switch panes (vim-style) |
| `Enter` | Select file / View record details |
| `s` | Toggle synchronized scrolling |
| `d` | Toggle diff highlighting |
| `e` / `c` | Expand / Collapse all nodes |
| `x` | Export current record |
| `Esc` / `b` | Go back |
| `q` | Quit |

## Automated Verification (Tests)

The test suite verifies conversation integrity automatically:

```bash
# Run all dataset mixer tests (60 tests)
uv run python -m pytest tests/test_dataset_mixer.py -v

# Run only the source filtering tests (15 tests)
uv run python -m pytest tests/test_dataset_mixer.py::TestSourceFiltering -v
```

Key test classes:
- `TestNemotronAdapterIntegrity` — conversations pass through unchanged
- `TestMessagesJSONLAdapterIntegrity` — messages renamed to conversations, content preserved
- `TestPromptCompletionCSVAdapterIntegrity` — prompt becomes user content, completion becomes assistant content
- `TestMixOutputIntegrity` — end-to-end mix verification (schema, counts, round-trip)
- `TestSourceFiltering` — include/exclude filtering produces correct subsets

## Dry-Run Verification

Preview record counts per source without writing files:

```bash
# All sources
uv run python -m scripts.dataset_mixer datasets/ --dry-run

# Nemotron only
uv run python -m scripts.dataset_mixer datasets/ --dry-run --include Nemotron-Terminal-Corpus

# Non-Nemotron
uv run python -m scripts.dataset_mixer datasets/ --dry-run --exclude Nemotron-Terminal-Corpus
```

## Expected Record Counts

| Mix | Source | Records |
|-----|--------|---------|
| Full | Nemotron Terminal Corpus | ~368,413 |
| Full | TeichAI math-3k | 3,317 |
| Full | Raiden Speciale | 8,041 |
| **Full total** | | **~379,771** |
| Nemotron only | Nemotron Terminal Corpus | ~368,413 |
| Non-Nemotron | TeichAI + Raiden | 11,358 |

> **Note:** `Raiden_Mini_Comparative.csv` (8,041 rows) is automatically excluded because it lacks `prompt`/`completion` columns. It contains the same prompts as the Speciale CSV but with two alternative model completions under different column names (`v3.2_speciale_completion`, `v3.2_completion`).
