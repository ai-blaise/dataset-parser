"""Integration tests with real data files from ./dataset/ directory.

These tests verify that the multi-format loaders work correctly with
actual dataset files. Tests are skipped if the data files don't exist.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from scripts.data_formats import (
    detect_format,
    get_loader,
    normalize_record,
    ParquetLoader,
    JSONLLoader,
)
from scripts.tui.data_loader import (
    load_records,
    load_all_records,
    load_record_at_index,
    get_record_summary,
    clear_cache,
)


# Path to dataset directory
DATASET_DIR = Path(__file__).parent.parent / "dataset"

# Real data files
PARQUET_FILE = DATASET_DIR / "train-00000-of-00001.parquet"
JSONL_FILE = DATASET_DIR / "interactive_agent.jsonl"
LARGE_JSONL_FILE = DATASET_DIR / "tool_calling.jsonl"


@pytest.fixture(autouse=True)
def clear_cache_before_each():
    """Clear cache before each test."""
    clear_cache()
    yield
    clear_cache()


# Skip conditions
requires_parquet = pytest.mark.skipif(
    not PARQUET_FILE.exists(),
    reason=f"Parquet file not found: {PARQUET_FILE}"
)

requires_jsonl = pytest.mark.skipif(
    not JSONL_FILE.exists(),
    reason=f"JSONL file not found: {JSONL_FILE}"
)

requires_large_jsonl = pytest.mark.skipif(
    not LARGE_JSONL_FILE.exists(),
    reason=f"Large JSONL file not found: {LARGE_JSONL_FILE}"
)


class TestRealParquetFile:
    """Tests with the real Parquet dataset file."""

    @requires_parquet
    def test_detect_parquet_format(self):
        """detect_format should identify Parquet file."""
        format_name = detect_format(str(PARQUET_FILE))
        assert format_name == "parquet"

    @requires_parquet
    def test_get_parquet_loader(self):
        """get_loader should return ParquetLoader for .parquet file."""
        loader = get_loader(str(PARQUET_FILE))
        assert isinstance(loader, ParquetLoader)

    @requires_parquet
    def test_get_record_count(self):
        """ParquetLoader should return record count from metadata."""
        loader = ParquetLoader()
        count = loader.get_record_count(str(PARQUET_FILE))
        assert count > 0
        print(f"Parquet file has {count} records")

    @requires_parquet
    def test_load_first_records(self):
        """Should load first few records from Parquet file."""
        loaded = list(load_records(str(PARQUET_FILE)))[:5]
        assert len(loaded) == 5

        for record in loaded:
            # Normalized records should have 'messages' not 'conversations'
            assert "messages" in record
            # Should have a uuid (from trial_name fallback)
            assert record.get("uuid") is not None

    @requires_parquet
    def test_parquet_record_structure(self):
        """Verify structure of loaded Parquet records."""
        record = load_record_at_index(str(PARQUET_FILE), 0)

        # Should have normalized messages
        assert "messages" in record
        messages = record["messages"]
        assert isinstance(messages, list)

        # Each message should have role and content
        if messages:
            first_msg = messages[0]
            assert "role" in first_msg
            assert "content" in first_msg

    @requires_parquet
    def test_parquet_random_access(self):
        """Test random access to Parquet records."""
        loader = ParquetLoader()
        count = loader.get_record_count(str(PARQUET_FILE))

        # Access first record
        first = load_record_at_index(str(PARQUET_FILE), 0)
        assert first is not None

        # Access middle record
        mid_idx = count // 2
        middle = load_record_at_index(str(PARQUET_FILE), mid_idx)
        assert middle is not None

        # Access last record
        last = load_record_at_index(str(PARQUET_FILE), count - 1)
        assert last is not None

    @requires_parquet
    def test_parquet_record_summary(self):
        """Test record summary generation for Parquet records."""
        record = load_record_at_index(str(PARQUET_FILE), 0)
        summary = get_record_summary(record, 0)

        assert summary["index"] == 0
        assert "msg_count" in summary
        assert "tool_count" in summary
        assert "preview" in summary


class TestRealJSONLFile:
    """Tests with the real JSONL dataset file."""

    @requires_jsonl
    def test_detect_jsonl_format(self):
        """detect_format should identify JSONL file."""
        format_name = detect_format(str(JSONL_FILE))
        assert format_name == "jsonl"

    @requires_jsonl
    def test_get_jsonl_loader(self):
        """get_loader should return JSONLLoader for .jsonl file."""
        loader = get_loader(str(JSONL_FILE))
        assert isinstance(loader, JSONLLoader)

    @requires_jsonl
    def test_load_first_records(self):
        """Should load first few records from JSONL file."""
        loaded = list(load_records(str(JSONL_FILE)))[:5]
        assert len(loaded) == 5

        for record in loaded:
            # JSONL records should have standard fields
            assert "messages" in record
            assert "uuid" in record

    @requires_jsonl
    def test_jsonl_record_structure(self):
        """Verify structure of loaded JSONL records."""
        record = load_record_at_index(str(JSONL_FILE), 0)

        # Standard JSONL fields
        assert "uuid" in record
        assert "messages" in record
        assert "tools" in record
        assert "license" in record

        # Messages structure
        messages = record["messages"]
        assert isinstance(messages, list)
        if messages:
            assert "role" in messages[0]
            assert "content" in messages[0]

    @requires_jsonl
    def test_jsonl_random_access(self):
        """Test random access to JSONL records."""
        # Load a few records to test
        records = load_all_records(str(JSONL_FILE), max_records=100)

        # Access specific indices
        r0 = load_record_at_index(str(JSONL_FILE), 0)
        r50 = load_record_at_index(str(JSONL_FILE), 50)
        r99 = load_record_at_index(str(JSONL_FILE), 99)

        assert r0["uuid"] == records[0]["uuid"]
        assert r50["uuid"] == records[50]["uuid"]
        assert r99["uuid"] == records[99]["uuid"]

    @requires_jsonl
    def test_jsonl_record_summary(self):
        """Test record summary generation for JSONL records."""
        record = load_record_at_index(str(JSONL_FILE), 0)
        summary = get_record_summary(record, 0)

        assert summary["index"] == 0
        assert "msg_count" in summary
        assert "tool_count" in summary
        assert "license" in summary
        assert "preview" in summary


class TestCrossFormatConsistency:
    """Tests comparing records across different formats."""

    @requires_parquet
    @requires_jsonl
    def test_normalized_records_have_same_structure(self):
        """Records from different formats should have same normalized structure."""
        # Load one record from each format
        parquet_record = load_record_at_index(str(PARQUET_FILE), 0)
        jsonl_record = load_record_at_index(str(JSONL_FILE), 0)

        # Both should have messages (not conversations)
        assert "messages" in parquet_record
        assert "messages" in jsonl_record

        # Both should have standard fields (with defaults if missing)
        for field in ["uuid", "messages", "tools", "license", "used_in"]:
            assert field in parquet_record, f"Parquet record missing {field}"
            assert field in jsonl_record, f"JSONL record missing {field}"

    @requires_parquet
    @requires_jsonl
    def test_record_summaries_have_same_keys(self):
        """Record summaries should have same keys regardless of source format."""
        parquet_record = load_record_at_index(str(PARQUET_FILE), 0)
        jsonl_record = load_record_at_index(str(JSONL_FILE), 0)

        parquet_summary = get_record_summary(parquet_record, 0)
        jsonl_summary = get_record_summary(jsonl_record, 0)

        # Same keys
        assert set(parquet_summary.keys()) == set(jsonl_summary.keys())


class TestLargeFileHandling:
    """Tests for handling large files efficiently."""

    @requires_large_jsonl
    def test_lazy_loading_large_file(self):
        """Should be able to iterate large file without loading all into memory."""
        # Just load first 10 records - should be fast
        count = 0
        for record in load_records(str(LARGE_JSONL_FILE)):
            count += 1
            if count >= 10:
                break

        assert count == 10

    @requires_parquet
    def test_parquet_record_count_without_full_load(self):
        """Parquet record count should be fast (uses metadata)."""
        loader = ParquetLoader()
        # This should be very fast - just reads metadata
        count = loader.get_record_count(str(PARQUET_FILE))
        assert count > 0


class TestMessageContent:
    """Tests verifying message content is loaded correctly."""

    @requires_parquet
    def test_parquet_message_content_preserved(self):
        """Message content should be fully preserved from Parquet."""
        record = load_record_at_index(str(PARQUET_FILE), 0)
        messages = record["messages"]

        # Find an assistant message with content
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                # Content should be a non-empty string
                assert isinstance(msg["content"], str)
                assert len(msg["content"]) > 0
                break

    @requires_jsonl
    def test_jsonl_message_content_preserved(self):
        """Message content should be fully preserved from JSONL."""
        record = load_record_at_index(str(JSONL_FILE), 0)
        messages = record["messages"]

        # Find an assistant message with content
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                # Content should be a non-empty string
                assert isinstance(msg["content"], str)
                assert len(msg["content"]) > 0
                break

    @requires_jsonl
    def test_jsonl_tool_calls_preserved(self):
        """Tool calls in messages should be preserved."""
        # Look through first 100 records for one with tool_calls
        for record in load_all_records(str(JSONL_FILE), max_records=100):
            for msg in record.get("messages", []):
                if "tool_calls" in msg:
                    tool_calls = msg["tool_calls"]
                    assert isinstance(tool_calls, list)
                    if tool_calls:
                        tc = tool_calls[0]
                        assert "function" in tc or "id" in tc
                    return  # Found one, test passes

        # If no tool_calls found in first 100, that's ok - just skip
        pytest.skip("No tool_calls found in first 100 records")


class TestToolDefinitions:
    """Tests for tool definitions in records."""

    @requires_jsonl
    def test_jsonl_tools_loaded(self):
        """Tool definitions should be loaded from JSONL."""
        # Look for a record with tools
        for record in load_all_records(str(JSONL_FILE), max_records=100):
            if record.get("tools"):
                tools = record["tools"]
                assert isinstance(tools, list)
                if tools:
                    tool = tools[0]
                    # Tool should have function info
                    assert "function" in tool or "type" in tool
                return

        pytest.skip("No records with tools found in first 100 records")
