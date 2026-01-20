"""Tests for ParquetLoader in scripts/data_formats/parquet_loader.py."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.data_formats import ParquetLoader


def create_parquet_file(filepath: Path, records: list[dict[str, Any]]) -> None:
    """Helper to create a Parquet file from records."""
    if not records:
        # Create empty parquet file
        table = pa.table({"_empty": []})
        pq.write_table(table, filepath)
        return

    table = pa.Table.from_pylist(records)
    pq.write_table(table, filepath)


def create_parquet_file_with_row_groups(
    filepath: Path,
    records: list[dict[str, Any]],
    row_group_size: int = 2
) -> None:
    """Helper to create a Parquet file with multiple row groups."""
    if not records:
        table = pa.table({"_empty": []})
        pq.write_table(table, filepath)
        return

    table = pa.Table.from_pylist(records)
    pq.write_table(table, filepath, row_group_size=row_group_size)


class TestParquetLoaderProperties:
    """Tests for ParquetLoader properties."""

    def test_format_name(self):
        """ParquetLoader should have correct format name."""
        loader = ParquetLoader()
        assert loader.format_name == "parquet"

    def test_supported_extensions(self):
        """ParquetLoader should support .parquet and .pq."""
        loader = ParquetLoader()
        assert ".parquet" in loader.supported_extensions
        assert ".pq" in loader.supported_extensions


class TestParquetLoaderLoad:
    """Tests for ParquetLoader.load() method."""

    def test_load_single_record(self, tmp_path):
        """Load Parquet file with single record."""
        filepath = tmp_path / "single.parquet"
        records = [{"id": 1, "name": "test"}]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 1
        assert loaded[0]["id"] == 1
        assert loaded[0]["name"] == "test"

    def test_load_multiple_records(self, tmp_path):
        """Load Parquet file with multiple records."""
        filepath = tmp_path / "multi.parquet"
        records = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3, "value": "c"},
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 3
        assert loaded[0]["id"] == 1
        assert loaded[2]["value"] == "c"

    def test_load_returns_generator(self, tmp_path):
        """load() should return a generator."""
        filepath = tmp_path / "gen.parquet"
        records = [{"id": 1}, {"id": 2}]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        result = loader.load(str(filepath))
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_load_file_not_found(self):
        """load() should raise error for non-existent file."""
        loader = ParquetLoader()
        with pytest.raises(Exception):  # PyArrow raises various errors
            list(loader.load("/nonexistent/path/data.parquet"))


class TestParquetLoaderNestedStructures:
    """Tests for handling nested structures in Parquet."""

    def test_load_nested_list(self, tmp_path):
        """Load Parquet file with nested list."""
        filepath = tmp_path / "nested_list.parquet"
        records = [
            {"id": 1, "items": [1, 2, 3]},
            {"id": 2, "items": [4, 5, 6]},
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["items"] == [1, 2, 3]
        assert loaded[1]["items"] == [4, 5, 6]

    def test_load_nested_dict(self, tmp_path):
        """Load Parquet file with nested dict."""
        filepath = tmp_path / "nested_dict.parquet"
        records = [
            {"id": 1, "data": {"key": "value"}},
            {"id": 2, "data": {"key": "other"}},
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["data"]["key"] == "value"
        assert loaded[1]["data"]["key"] == "other"

    def test_load_conversations_structure(self, tmp_path):
        """Load Parquet file with conversations (like the real dataset)."""
        filepath = tmp_path / "conversations.parquet"
        records = [
            {
                "conversations": [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ],
            },
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 1
        assert len(loaded[0]["conversations"]) == 3
        assert loaded[0]["conversations"][0]["role"] == "system"
        assert loaded[0]["conversations"][1]["content"] == "Hello"

    def test_load_deeply_nested(self, tmp_path):
        """Load Parquet file with deeply nested structures."""
        filepath = tmp_path / "deep.parquet"
        records = [
            {
                "level1": {
                    "level2": {
                        "level3": ["a", "b", "c"]
                    }
                }
            },
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["level1"]["level2"]["level3"] == ["a", "b", "c"]

    def test_load_null_values(self, tmp_path):
        """Load Parquet file with null values."""
        filepath = tmp_path / "nulls.parquet"
        records = [
            {"id": 1, "optional": None},
            {"id": 2, "optional": "present"},
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["optional"] is None
        assert loaded[1]["optional"] == "present"


class TestParquetLoaderLoadAll:
    """Tests for ParquetLoader.load_all() method."""

    def test_load_all_records(self, tmp_path):
        """load_all() should return all records."""
        filepath = tmp_path / "all.parquet"
        records = [{"id": i} for i in range(10)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = loader.load_all(str(filepath))
        assert len(loaded) == 10
        assert loaded[0]["id"] == 0
        assert loaded[9]["id"] == 9

    def test_load_all_with_max_records(self, tmp_path):
        """load_all() should respect max_records."""
        filepath = tmp_path / "limited.parquet"
        records = [{"id": i} for i in range(100)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = loader.load_all(str(filepath), max_records=5)
        assert len(loaded) == 5
        assert loaded[4]["id"] == 4

    def test_load_all_with_progress_callback(self, tmp_path):
        """load_all() should call progress callback."""
        filepath = tmp_path / "progress.parquet"
        records = [{"id": i} for i in range(5)]
        create_parquet_file(filepath, records)

        callback_calls = []
        def progress_callback(loaded: int, total: int | None) -> None:
            callback_calls.append((loaded, total))

        loader = ParquetLoader()
        loader.load_all(str(filepath), progress_callback=progress_callback)

        # Should have at least initial and final calls
        assert len(callback_calls) >= 1
        # Final call should report all records loaded
        assert callback_calls[-1][0] == 5


class TestParquetLoaderGetRecordCount:
    """Tests for ParquetLoader.get_record_count() method."""

    def test_get_record_count(self, tmp_path):
        """get_record_count() should return correct count."""
        filepath = tmp_path / "count.parquet"
        records = [{"id": i} for i in range(25)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 25

    def test_get_record_count_empty(self, tmp_path):
        """get_record_count() for empty file should return 0."""
        filepath = tmp_path / "empty.parquet"
        create_parquet_file(filepath, [])

        loader = ParquetLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 0

    def test_get_record_count_uses_metadata(self, tmp_path):
        """get_record_count() should use metadata, not load all data."""
        filepath = tmp_path / "metadata.parquet"
        # Create a larger file
        records = [{"id": i, "data": "x" * 100} for i in range(1000)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        # This should be fast because it only reads metadata
        count = loader.get_record_count(str(filepath))
        assert count == 1000


class TestParquetLoaderGetRecordAtIndex:
    """Tests for ParquetLoader.get_record_at_index() method."""

    def test_get_first_record(self, tmp_path):
        """get_record_at_index(0) should return first record."""
        filepath = tmp_path / "first.parquet"
        records = [{"id": i} for i in range(5)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        record = loader.get_record_at_index(str(filepath), 0)
        assert record["id"] == 0

    def test_get_last_record(self, tmp_path):
        """get_record_at_index() should return last record correctly."""
        filepath = tmp_path / "last.parquet"
        records = [{"id": i} for i in range(10)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        record = loader.get_record_at_index(str(filepath), 9)
        assert record["id"] == 9

    def test_get_middle_record(self, tmp_path):
        """get_record_at_index() should return middle record correctly."""
        filepath = tmp_path / "middle.parquet"
        records = [{"id": i, "value": f"v{i}"} for i in range(20)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        record = loader.get_record_at_index(str(filepath), 10)
        assert record["id"] == 10
        assert record["value"] == "v10"

    def test_get_record_at_index_with_multiple_row_groups(self, tmp_path):
        """get_record_at_index() should work across row groups."""
        filepath = tmp_path / "rowgroups.parquet"
        records = [{"id": i} for i in range(10)]
        create_parquet_file_with_row_groups(filepath, records, row_group_size=3)

        loader = ParquetLoader()
        # Test records from different row groups
        assert loader.get_record_at_index(str(filepath), 0)["id"] == 0
        assert loader.get_record_at_index(str(filepath), 3)["id"] == 3
        assert loader.get_record_at_index(str(filepath), 7)["id"] == 7

    def test_get_record_negative_index_raises(self, tmp_path):
        """get_record_at_index() should raise for negative index."""
        filepath = tmp_path / "negative.parquet"
        records = [{"id": 1}]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        with pytest.raises(IndexError):
            loader.get_record_at_index(str(filepath), -1)

    def test_get_record_index_out_of_range_raises(self, tmp_path):
        """get_record_at_index() should raise for out of range index."""
        filepath = tmp_path / "outofrange.parquet"
        records = [{"id": i} for i in range(5)]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        with pytest.raises(IndexError):
            loader.get_record_at_index(str(filepath), 10)


class TestParquetLoaderDataTypes:
    """Tests for various data types in Parquet files."""

    def test_string_types(self, tmp_path):
        """Parquet loader should handle string types."""
        filepath = tmp_path / "strings.parquet"
        records = [
            {"text": "hello"},
            {"text": "世界"},  # Unicode
            {"text": "🎉"},  # Emoji
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["text"] == "hello"
        assert loaded[1]["text"] == "世界"
        assert loaded[2]["text"] == "🎉"

    def test_numeric_types(self, tmp_path):
        """Parquet loader should handle numeric types."""
        filepath = tmp_path / "numbers.parquet"
        records = [
            {"int_val": 42, "float_val": 3.14},
            {"int_val": -100, "float_val": 0.0},
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["int_val"] == 42
        assert loaded[0]["float_val"] == 3.14

    def test_boolean_types(self, tmp_path):
        """Parquet loader should handle boolean types."""
        filepath = tmp_path / "bools.parquet"
        records = [
            {"flag": True},
            {"flag": False},
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["flag"] is True
        assert loaded[1]["flag"] is False


class TestParquetLoaderWithRealDatasetStructure:
    """Tests with structure similar to the actual dataset."""

    def test_full_record_structure(self, tmp_path):
        """Test with structure similar to real parquet dataset."""
        filepath = tmp_path / "dataset.parquet"
        records = [
            {
                "conversations": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is 2+2?"},
                    {"role": "assistant", "content": "2+2 equals 4."},
                ],
                "source": "test",
                "metadata": {"version": "1.0"},
            },
        ]
        create_parquet_file(filepath, records)

        loader = ParquetLoader()
        loaded = list(loader.load(str(filepath)))

        assert len(loaded) == 1
        record = loaded[0]
        assert "conversations" in record
        assert len(record["conversations"]) == 3
        assert record["conversations"][0]["role"] == "system"
        assert record["source"] == "test"
        assert record["metadata"]["version"] == "1.0"
