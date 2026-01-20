# Data Generation Script Plan

## Overview

Create a script that takes output from `parser_finale.py` (records with emptied assistant content) and uses an LLM API to fill in the assistant responses. The script uses OpenAI-compatible endpoints (works with any provider including sglang).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Generation Flow                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  .env file                    parser_finale.py output               │
│  ┌──────────────┐             ┌──────────────────────┐              │
│  │ BASE_URL     │             │ Records with empty   │              │
│  │ API_KEY      │             │ assistant content    │              │
│  └──────┬───────┘             └──────────┬───────────┘              │
│         │                                │                          │
│         └────────────┬───────────────────┘                          │
│                      ▼                                              │
│              ┌───────────────┐                                      │
│              │  data_gen.py  │                                      │
│              └───────┬───────┘                                      │
│                      │                                              │
│                      ▼                                              │
│           ┌─────────────────────┐                                   │
│           │  OpenAI-compatible  │                                   │
│           │     endpoint        │                                   │
│           └──────────┬──────────┘                                   │
│                      │                                              │
│                      ▼                                              │
│           ┌─────────────────┐                                       │
│           │ Output: Records │                                       │
│           │ with filled     │                                       │
│           │ assistant       │                                       │
│           │ content         │                                       │
│           └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Environment Configuration

### .env File Structure

```bash
# Required
BASE_URL=https://api.openai.com/v1   # Any OpenAI-compatible endpoint (sglang, vllm, etc.)
API_KEY=sk-...                        # API key (use "dummy" for sglang)
```

### Loading Environment Variables

```python
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
```

---

## Input Format

The script accepts output from `parser_finale.py` in any of these formats:
- **JSONL** (preferred for streaming)
- **JSON** (array of records)
- **Parquet**

### Input Record Structure

Records from `parser_finale.py` have this structure:

```json
{
  "uuid": "unique-identifier",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant..."},
    {"role": "user", "content": "User's question"},
    {"role": "assistant", "content": ""}
  ],
  "tools": [...],
  "license": "cc-by-4.0",
  "used_in": ["nano_v3"]
}
```

**Key observation**: Assistant messages have `content: ""` that needs to be filled.

---

## Core API Function

The script has one core function that calls the endpoint and returns a response:

```python
from openai import OpenAI

def call_llm(messages: list, base_url: str, api_key: str) -> str:
    """
    Call an OpenAI-compatible endpoint and return the assistant response.

    Args:
        messages: List of message dicts with 'role' and 'content'
        base_url: API endpoint URL
        api_key: API key (use "dummy" for sglang)

    Returns:
        The assistant's response content as a string
    """
    client = OpenAI(base_url=base_url, api_key=api_key)

    response = client.chat.completions.create(
        model="default",
        messages=messages,
    )

    return response.choices[0].message.content
```

This function is intentionally simple - it just sends messages to the endpoint and returns the response.

---

## CLI Interface

### Command Structure

```bash
uv run python -m scripts.data_gen <input_file> [options]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output FILE` | Output file path | stdout |
| `-f, --output-format {json,jsonl,parquet}` | Output format | jsonl |
| `--input-format {auto,json,jsonl,parquet}` | Input format | auto |
| `--env FILE` | Path to .env file | .env |
| `--dry-run` | Show what would be processed | false |
| `--start N` | Start from record N | 0 |
| `--end N` | End at record N | end |
| `-i, --index N` | Process single record | all |
| `--verbose` | Show progress and stats | false |
| `--skip-existing` | Skip records with content | false |

### Usage Examples

```bash
# Basic usage
uv run python -m scripts.data_gen processed.jsonl -o filled.jsonl

# With different .env file
uv run python -m scripts.data_gen processed.jsonl --env .env.local -o filled.jsonl

# Dry run to see what would be processed
uv run python -m scripts.data_gen processed.jsonl --dry-run

# Process range of records
uv run python -m scripts.data_gen processed.jsonl --start 0 --end 100 -o batch1.jsonl

# Verbose mode with parquet output
uv run python -m scripts.data_gen processed.parquet -f parquet -o filled.parquet --verbose
```

---

## Implementation Steps

### Phase 1: Core Infrastructure

1. **Create script skeleton** (`scripts/data_gen.py`)
   - Argument parsing with argparse
   - Environment loading with python-dotenv
   - Configuration validation

2. **Add dependencies to pyproject.toml**
   ```toml
   dependencies = [
       "textual>=7.3.0",
       "pyarrow>=15.0.0",
       "python-dotenv>=1.0.0",  # NEW
       "openai>=1.0.0",          # NEW
   ]
   ```

3. **Create .env.example template**
   ```bash
   BASE_URL=https://api.openai.com/v1
   API_KEY=your-api-key-here
   ```

### Phase 2: Data Loading Integration

4. **Integrate existing data loaders**
   - Reuse `scripts/data_formats/` loaders (JSONLoader, JSONLLoader, ParquetLoader)
   - Reuse `scripts/data_formats/schema_normalizer.py` for normalization

5. **Implement record iterator**
   - Lazy loading for memory efficiency
   - Support for range filtering (--start, --end)
   - Progress tracking

### Phase 3: API Function

6. **Implement the `call_llm` function**
   - Simple function that takes messages, base_url, api_key
   - Returns the assistant response content
   - Uses OpenAI SDK (works with any OpenAI-compatible endpoint)

### Phase 4: Processing Logic

7. **Build processing loop**
   - For each record, find empty assistant messages
   - Build context (messages up to that point)
   - Call `call_llm` to get response
   - Fill in the assistant content

### Phase 5: Output Generation

8. **Implement output writers**
   - Reuse existing format writers
   - Write filled records to output file

### Phase 6: Testing

9. **Unit tests**
   - Test environment loading
   - Test `call_llm` function with mocked responses
   - Test record processing

10. **Integration tests**
    - Test with sample records
    - Test different output formats

---

## Error Handling

| Error Type | Handling |
|------------|----------|
| API error | Log error, skip record |
| Missing .env values | Abort with clear message |
| Invalid record format | Log warning, skip record |
| Empty input file | Exit with error |

---

## Output Format

Output maintains the same structure as input, with filled assistant content:

```json
{
  "uuid": "unique-identifier",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant..."},
    {"role": "user", "content": "User's question"},
    {
      "role": "assistant",
      "content": "Here is my response..."  // FILLED
    }
  ],
  "tools": [...],
  "license": "cc-by-4.0",
  "used_in": ["nano_v3"]
}
```

---

## File Structure

```
scripts/
├── data_gen.py          # Main script (NEW)
├── data_formats/        # Existing loaders
│   ├── __init__.py
│   ├── json_loader.py
│   ├── jsonl_loader.py
│   ├── parquet_loader.py
│   └── schema_normalizer.py
├── parser_finale.py     # Existing parser
├── main.py              # Existing CLI
└── tui/                 # Existing TUI

tests/
├── test_data_gen.py     # Unit tests (NEW)
└── ...

.env.example             # Template (NEW)
.env                     # User config (gitignored)
```

---

## Dependencies

### New Dependencies

```toml
# pyproject.toml additions
dependencies = [
    "python-dotenv>=1.0.0",  # Environment variable loading
    "openai>=1.0.0",          # OpenAI-compatible API client
]
```

---

## Future Enhancements

1. **Resume capability** - Save progress and resume interrupted processing
2. **Concurrent requests** - Process multiple records in parallel
3. **Caching** - Cache identical prompts to avoid duplicate API calls
