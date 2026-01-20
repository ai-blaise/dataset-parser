"""Tests for JSONLoader in scripts/data_formats/json_loader.py."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any

from scripts.data_formats import JSONLoader


class TestJSONLoaderProperties:
    """Tests for JSONLoader properties."""

    def test_format_name(self):
        """JSONLoader should have correct format name."""
        loader = JSONLoader()
        assert loader.format_name == "json"

    def test_supported_extensions(self):
        """JSONLoader should support .json extension."""
        loader = JSONLoader()
        assert ".json" in loader.supported_extensions


class TestJSONLoaderLoadArray:
    """Tests for JSONLoader.load() with array input."""

    def test_load_empty_array(self, tmp_path):
        """Load JSON file with empty array."""
        filepath = tmp_path / "empty.json"
        filepath.write_text("[]")

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 0

    def test_load_single_element_array(self, tmp_path):
        """Load JSON file with single element array."""
        filepath = tmp_path / "single.json"
        filepath.write_text('[{"id": 1}]')

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 1
        assert loaded[0]["id"] == 1

    def test_load_multiple_element_array(self, tmp_path):
        """Load JSON file with multiple elements."""
        filepath = tmp_path / "multi.json"
        data = [{"id": i} for i in range(5)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 5
        assert loaded[0]["id"] == 0
        assert loaded[4]["id"] == 4

    def test_load_preserves_order(self, tmp_path):
        """Load should preserve array order."""
        filepath = tmp_path / "ordered.json"
        data = [{"value": "first"}, {"value": "second"}, {"value": "third"}]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["value"] == "first"
        assert loaded[1]["value"] == "second"
        assert loaded[2]["value"] == "third"


class TestJSONLoaderLoadSingleObject:
    """Tests for JSONLoader.load() with single object input."""

    def test_load_single_object(self, tmp_path):
        """Load JSON file with single object (not array)."""
        filepath = tmp_path / "single_obj.json"
        filepath.write_text('{"id": 42, "name": "test"}')

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 1
        assert loaded[0]["id"] == 42
        assert loaded[0]["name"] == "test"

    def test_load_empty_object(self, tmp_path):
        """Load JSON file with empty object."""
        filepath = tmp_path / "empty_obj.json"
        filepath.write_text("{}")

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 1
        assert loaded[0] == {}


class TestJSONLoaderLoadNestedStructures:
    """Tests for loading nested structures in JSON files."""

    def test_load_nested_objects(self, tmp_path):
        """Load JSON with nested objects."""
        filepath = tmp_path / "nested.json"
        data = [{"outer": {"inner": {"deep": "value"}}}]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["outer"]["inner"]["deep"] == "value"

    def test_load_nested_arrays(self, tmp_path):
        """Load JSON with nested arrays."""
        filepath = tmp_path / "arrays.json"
        data = [{"items": [[1, 2], [3, 4]]}]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["items"] == [[1, 2], [3, 4]]

    def test_load_conversation_structure(self, tmp_path):
        """Load JSON with conversation-like structure."""
        filepath = tmp_path / "conversation.json"
        data = [
            {
                "messages": [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ],
                "tools": [],
            }
        ]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded[0]["messages"]) == 3
        assert loaded[0]["messages"][0]["role"] == "system"


class TestJSONLoaderLoadDataTypes:
    """Tests for various JSON data types."""

    def test_load_string_values(self, tmp_path):
        """Load JSON with string values."""
        filepath = tmp_path / "strings.json"
        data = [{"text": "hello"}, {"text": "世界"}, {"text": "🎉"}]
        filepath.write_text(json.dumps(data, ensure_ascii=False))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["text"] == "hello"
        assert loaded[1]["text"] == "世界"
        assert loaded[2]["text"] == "🎉"

    def test_load_numeric_values(self, tmp_path):
        """Load JSON with numeric values."""
        filepath = tmp_path / "numbers.json"
        data = [{"int": 42, "float": 3.14, "negative": -100}]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["int"] == 42
        assert loaded[0]["float"] == 3.14
        assert loaded[0]["negative"] == -100

    def test_load_boolean_values(self, tmp_path):
        """Load JSON with boolean values."""
        filepath = tmp_path / "bools.json"
        data = [{"yes": True, "no": False}]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["yes"] is True
        assert loaded[0]["no"] is False

    def test_load_null_values(self, tmp_path):
        """Load JSON with null values."""
        filepath = tmp_path / "nulls.json"
        data = [{"present": "value", "absent": None}]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert loaded[0]["present"] == "value"
        assert loaded[0]["absent"] is None


class TestJSONLoaderLoadErrors:
    """Tests for error handling in load()."""

    def test_load_file_not_found(self):
        """load() should raise FileNotFoundError for non-existent file."""
        loader = JSONLoader()
        with pytest.raises(FileNotFoundError):
            list(loader.load("/nonexistent/path/data.json"))

    def test_load_invalid_json(self, tmp_path):
        """load() should raise JSONDecodeError for invalid JSON."""
        filepath = tmp_path / "invalid.json"
        filepath.write_text("{invalid json}")

        loader = JSONLoader()
        with pytest.raises(json.JSONDecodeError):
            list(loader.load(str(filepath)))

    def test_load_non_object_array_item(self, tmp_path):
        """load() should raise ValueError for non-object array items."""
        filepath = tmp_path / "bad_array.json"
        filepath.write_text('[{"ok": true}, "not an object", {"ok": true}]')

        loader = JSONLoader()
        with pytest.raises(ValueError, match="not an object"):
            list(loader.load(str(filepath)))

    def test_load_primitive_value(self, tmp_path):
        """load() should raise ValueError for primitive values."""
        filepath = tmp_path / "primitive.json"
        filepath.write_text('"just a string"')

        loader = JSONLoader()
        with pytest.raises(ValueError, match="must contain an object or array"):
            list(loader.load(str(filepath)))

    def test_load_number_primitive(self, tmp_path):
        """load() should raise ValueError for number primitives."""
        filepath = tmp_path / "number.json"
        filepath.write_text("42")

        loader = JSONLoader()
        with pytest.raises(ValueError, match="must contain an object or array"):
            list(loader.load(str(filepath)))


class TestJSONLoaderLoadAll:
    """Tests for JSONLoader.load_all() method."""

    def test_load_all_records(self, tmp_path):
        """load_all() should return all records."""
        filepath = tmp_path / "all.json"
        data = [{"id": i} for i in range(10)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = loader.load_all(str(filepath))
        assert len(loaded) == 10
        assert loaded[0]["id"] == 0
        assert loaded[9]["id"] == 9

    def test_load_all_with_max_records(self, tmp_path):
        """load_all() should respect max_records."""
        filepath = tmp_path / "limited.json"
        data = [{"id": i} for i in range(100)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = loader.load_all(str(filepath), max_records=5)
        assert len(loaded) == 5
        assert loaded[4]["id"] == 4

    def test_load_all_max_records_exceeds_total(self, tmp_path):
        """load_all() with max_records > total should return all."""
        filepath = tmp_path / "small.json"
        data = [{"id": i} for i in range(3)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        loaded = loader.load_all(str(filepath), max_records=100)
        assert len(loaded) == 3

    def test_load_all_with_progress_callback(self, tmp_path):
        """load_all() should call progress callback."""
        filepath = tmp_path / "progress.json"
        data = [{"id": i} for i in range(5)]
        filepath.write_text(json.dumps(data))

        callback_calls = []
        def progress_callback(loaded: int, total: int | None) -> None:
            callback_calls.append((loaded, total))

        loader = JSONLoader()
        loader.load_all(str(filepath), progress_callback=progress_callback)

        # Should have at least one call
        assert len(callback_calls) >= 1
        # Final call should report all records loaded
        assert callback_calls[-1][0] == 5


class TestJSONLoaderGetRecordCount:
    """Tests for JSONLoader.get_record_count() method."""

    def test_get_record_count_array(self, tmp_path):
        """get_record_count() should return correct count for arrays."""
        filepath = tmp_path / "count.json"
        data = [{"id": i} for i in range(25)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 25

    def test_get_record_count_single_object(self, tmp_path):
        """get_record_count() should return 1 for single object."""
        filepath = tmp_path / "single.json"
        filepath.write_text('{"id": 1}')

        loader = JSONLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 1

    def test_get_record_count_empty_array(self, tmp_path):
        """get_record_count() for empty array should return 0."""
        filepath = tmp_path / "empty.json"
        filepath.write_text("[]")

        loader = JSONLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 0


class TestJSONLoaderGetRecordAtIndex:
    """Tests for JSONLoader.get_record_at_index() method."""

    def test_get_first_record(self, tmp_path):
        """get_record_at_index(0) should return first record."""
        filepath = tmp_path / "first.json"
        data = [{"id": i} for i in range(5)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        record = loader.get_record_at_index(str(filepath), 0)
        assert record["id"] == 0

    def test_get_last_record(self, tmp_path):
        """get_record_at_index() should return last record correctly."""
        filepath = tmp_path / "last.json"
        data = [{"id": i} for i in range(10)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        record = loader.get_record_at_index(str(filepath), 9)
        assert record["id"] == 9

    def test_get_middle_record(self, tmp_path):
        """get_record_at_index() should return middle record correctly."""
        filepath = tmp_path / "middle.json"
        data = [{"id": i, "value": f"v{i}"} for i in range(20)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        record = loader.get_record_at_index(str(filepath), 10)
        assert record["id"] == 10
        assert record["value"] == "v10"

    def test_get_record_from_single_object(self, tmp_path):
        """get_record_at_index(0) should work for single object."""
        filepath = tmp_path / "single.json"
        filepath.write_text('{"id": 42}')

        loader = JSONLoader()
        record = loader.get_record_at_index(str(filepath), 0)
        assert record["id"] == 42

    def test_get_record_negative_index_raises(self, tmp_path):
        """get_record_at_index() should raise for negative index."""
        filepath = tmp_path / "negative.json"
        filepath.write_text('[{"id": 1}]')

        loader = JSONLoader()
        with pytest.raises(IndexError):
            loader.get_record_at_index(str(filepath), -1)

    def test_get_record_index_out_of_range_raises(self, tmp_path):
        """get_record_at_index() should raise for out of range index."""
        filepath = tmp_path / "outofrange.json"
        data = [{"id": i} for i in range(5)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()
        with pytest.raises(IndexError):
            loader.get_record_at_index(str(filepath), 10)

    def test_get_record_index_1_from_single_object_raises(self, tmp_path):
        """get_record_at_index(1) should raise for single object."""
        filepath = tmp_path / "single_oor.json"
        filepath.write_text('{"id": 1}')

        loader = JSONLoader()
        with pytest.raises(IndexError):
            loader.get_record_at_index(str(filepath), 1)


class TestJSONLoaderGenerator:
    """Tests for generator behavior of load()."""

    def test_load_returns_generator(self, tmp_path):
        """load() should return a generator."""
        filepath = tmp_path / "gen.json"
        filepath.write_text('[{"id": 1}, {"id": 2}]')

        loader = JSONLoader()
        result = loader.load(str(filepath))
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_load_can_iterate_multiple_times(self, tmp_path):
        """load() should allow creating new generators."""
        filepath = tmp_path / "multi_iter.json"
        data = [{"id": i} for i in range(3)]
        filepath.write_text(json.dumps(data))

        loader = JSONLoader()

        # First iteration
        first_pass = list(loader.load(str(filepath)))
        assert len(first_pass) == 3

        # Second iteration (new generator)
        second_pass = list(loader.load(str(filepath)))
        assert len(second_pass) == 3
        assert first_pass == second_pass


class TestJSONLoaderWithFormattedJSON:
    """Tests for handling formatted (pretty-printed) JSON."""

    def test_load_pretty_printed(self, tmp_path):
        """Load pretty-printed JSON."""
        filepath = tmp_path / "pretty.json"
        data = [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}]
        filepath.write_text(json.dumps(data, indent=2))

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 2
        assert loaded[0]["name"] == "test"

    def test_load_with_trailing_whitespace(self, tmp_path):
        """Load JSON with trailing whitespace."""
        filepath = tmp_path / "trailing.json"
        filepath.write_text('[{"id": 1}]   \n\n')

        loader = JSONLoader()
        loaded = list(loader.load(str(filepath)))
        assert len(loaded) == 1
