"""Tests for format detection in scripts/data_formats/format_detector.py."""

from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path

from scripts.data_formats import (
    detect_format,
    get_loader,
    get_loader_for_format,
    EXTENSION_MAP,
    SUPPORTED_FORMATS,
    JSONLLoader,
    JSONLoader,
    ParquetLoader,
)


class TestDetectFormat:
    """Tests for detect_format() function."""

    def test_detect_jsonl_extension(self, tmp_path):
        """Detect .jsonl files correctly."""
        filepath = tmp_path / "data.jsonl"
        filepath.write_text('{"test": 1}\n')
        assert detect_format(str(filepath)) == "jsonl"

    def test_detect_json_extension(self, tmp_path):
        """Detect .json files correctly."""
        filepath = tmp_path / "data.json"
        filepath.write_text('[{"test": 1}]')
        assert detect_format(str(filepath)) == "json"

    def test_detect_parquet_extension(self, tmp_path):
        """Detect .parquet files correctly."""
        filepath = tmp_path / "data.parquet"
        filepath.write_bytes(b"PAR1")  # Parquet magic bytes
        assert detect_format(str(filepath)) == "parquet"

    def test_detect_pq_extension(self, tmp_path):
        """Detect .pq files as parquet."""
        filepath = tmp_path / "data.pq"
        filepath.write_bytes(b"PAR1")
        assert detect_format(str(filepath)) == "parquet"

    def test_detect_uppercase_extension(self, tmp_path):
        """Handle uppercase extensions."""
        filepath = tmp_path / "DATA.JSONL"
        filepath.write_text('{"test": 1}\n')
        assert detect_format(str(filepath)) == "jsonl"

    def test_detect_mixed_case_extension(self, tmp_path):
        """Handle mixed case extensions."""
        filepath = tmp_path / "Data.Json"
        filepath.write_text('[{"test": 1}]')
        assert detect_format(str(filepath)) == "json"

    def test_unknown_extension_raises(self, tmp_path):
        """Unknown extension should raise ValueError."""
        filepath = tmp_path / "data.csv"
        filepath.write_text("a,b,c\n1,2,3")
        with pytest.raises(ValueError, match="Unsupported file format"):
            detect_format(str(filepath))

    def test_no_extension_raises(self, tmp_path):
        """File without extension should raise ValueError."""
        filepath = tmp_path / "datafile"
        filepath.write_text('{"test": 1}')
        with pytest.raises(ValueError, match="Unsupported file format"):
            detect_format(str(filepath))


class TestGetLoader:
    """Tests for get_loader() factory function."""

    def test_get_loader_jsonl(self, tmp_path):
        """Get correct loader for .jsonl files."""
        filepath = tmp_path / "data.jsonl"
        filepath.write_text('{"test": 1}\n')
        loader = get_loader(str(filepath))
        assert isinstance(loader, JSONLLoader)
        assert loader.format_name == "jsonl"

    def test_get_loader_json(self, tmp_path):
        """Get correct loader for .json files."""
        filepath = tmp_path / "data.json"
        filepath.write_text('[{"test": 1}]')
        loader = get_loader(str(filepath))
        assert isinstance(loader, JSONLoader)
        assert loader.format_name == "json"

    def test_get_loader_parquet(self, tmp_path):
        """Get correct loader for .parquet files."""
        filepath = tmp_path / "data.parquet"
        filepath.write_bytes(b"PAR1")  # Just need file to exist
        loader = get_loader(str(filepath))
        assert isinstance(loader, ParquetLoader)
        assert loader.format_name == "parquet"

    def test_get_loader_pq(self, tmp_path):
        """Get correct loader for .pq files."""
        filepath = tmp_path / "data.pq"
        filepath.write_bytes(b"PAR1")
        loader = get_loader(str(filepath))
        assert isinstance(loader, ParquetLoader)

    def test_get_loader_unknown_raises(self, tmp_path):
        """Unknown format should raise ValueError."""
        filepath = tmp_path / "data.xml"
        filepath.write_text("<root></root>")
        with pytest.raises(ValueError):
            get_loader(str(filepath))


class TestGetLoaderForFormat:
    """Tests for get_loader_for_format() function."""

    def test_get_loader_for_jsonl(self):
        """Get JSONL loader by format name."""
        loader = get_loader_for_format("jsonl")
        assert isinstance(loader, JSONLLoader)

    def test_get_loader_for_json(self):
        """Get JSON loader by format name."""
        loader = get_loader_for_format("json")
        assert isinstance(loader, JSONLoader)

    def test_get_loader_for_parquet(self):
        """Get Parquet loader by format name."""
        loader = get_loader_for_format("parquet")
        assert isinstance(loader, ParquetLoader)

    def test_get_loader_for_unknown_raises(self):
        """Unknown format name should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            get_loader_for_format("csv")


class TestExtensionMap:
    """Tests for EXTENSION_MAP constant."""

    def test_extension_map_has_jsonl(self):
        """Extension map should have .jsonl."""
        assert ".jsonl" in EXTENSION_MAP
        assert EXTENSION_MAP[".jsonl"] == "jsonl"

    def test_extension_map_has_json(self):
        """Extension map should have .json."""
        assert ".json" in EXTENSION_MAP
        assert EXTENSION_MAP[".json"] == "json"

    def test_extension_map_has_parquet(self):
        """Extension map should have .parquet."""
        assert ".parquet" in EXTENSION_MAP
        assert EXTENSION_MAP[".parquet"] == "parquet"

    def test_extension_map_has_pq(self):
        """Extension map should have .pq as parquet alias."""
        assert ".pq" in EXTENSION_MAP
        assert EXTENSION_MAP[".pq"] == "parquet"


class TestSupportedFormats:
    """Tests for SUPPORTED_FORMATS constant."""

    def test_supported_formats_includes_all(self):
        """SUPPORTED_FORMATS should include all format names."""
        assert "jsonl" in SUPPORTED_FORMATS
        assert "json" in SUPPORTED_FORMATS
        assert "parquet" in SUPPORTED_FORMATS

    def test_supported_formats_is_set(self):
        """SUPPORTED_FORMATS should be a set for efficient lookup."""
        assert isinstance(SUPPORTED_FORMATS, (set, frozenset))


class TestLoaderProperties:
    """Tests for loader properties."""

    def test_jsonl_loader_extensions(self):
        """JSONL loader should list supported extensions."""
        loader = JSONLLoader()
        assert ".jsonl" in loader.supported_extensions

    def test_json_loader_extensions(self):
        """JSON loader should list supported extensions."""
        loader = JSONLoader()
        assert ".json" in loader.supported_extensions

    def test_parquet_loader_extensions(self):
        """Parquet loader should list supported extensions."""
        loader = ParquetLoader()
        assert ".parquet" in loader.supported_extensions
        assert ".pq" in loader.supported_extensions

    def test_loader_format_names(self):
        """All loaders should have correct format names."""
        assert JSONLLoader().format_name == "jsonl"
        assert JSONLoader().format_name == "json"
        assert ParquetLoader().format_name == "parquet"


class TestLoaderLoad:
    """Tests for basic loading functionality."""

    def test_jsonl_loader_loads_records(self, tmp_path):
        """JSONL loader should load records correctly."""
        filepath = tmp_path / "data.jsonl"
        filepath.write_text('{"id": 1}\n{"id": 2}\n{"id": 3}\n')

        loader = JSONLLoader()
        records = list(loader.load(str(filepath)))
        assert len(records) == 3
        assert records[0]["id"] == 1
        assert records[2]["id"] == 3

    def test_json_loader_loads_array(self, tmp_path):
        """JSON loader should load array correctly."""
        filepath = tmp_path / "data.json"
        filepath.write_text('[{"id": 1}, {"id": 2}]')

        loader = JSONLoader()
        records = list(loader.load(str(filepath)))
        assert len(records) == 2
        assert records[0]["id"] == 1

    def test_json_loader_loads_single_object(self, tmp_path):
        """JSON loader should handle single object."""
        filepath = tmp_path / "data.json"
        filepath.write_text('{"id": 1, "name": "test"}')

        loader = JSONLoader()
        records = list(loader.load(str(filepath)))
        assert len(records) == 1
        assert records[0]["id"] == 1


class TestGetRecordCount:
    """Tests for get_record_count() method."""

    def test_jsonl_record_count(self, tmp_path):
        """JSONL loader should count records correctly."""
        filepath = tmp_path / "data.jsonl"
        filepath.write_text('{"a": 1}\n{"a": 2}\n{"a": 3}\n{"a": 4}\n')

        loader = JSONLLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 4

    def test_json_record_count_array(self, tmp_path):
        """JSON loader should count array elements."""
        filepath = tmp_path / "data.json"
        filepath.write_text('[{"a": 1}, {"a": 2}, {"a": 3}]')

        loader = JSONLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 3

    def test_json_record_count_single(self, tmp_path):
        """JSON loader should count single object as 1."""
        filepath = tmp_path / "data.json"
        filepath.write_text('{"a": 1}')

        loader = JSONLoader()
        count = loader.get_record_count(str(filepath))
        assert count == 1


class TestGetRecordAtIndex:
    """Tests for get_record_at_index() method."""

    def test_jsonl_get_record_at_index(self, tmp_path):
        """JSONL loader should get record by index."""
        filepath = tmp_path / "data.jsonl"
        filepath.write_text('{"id": 0}\n{"id": 1}\n{"id": 2}\n')

        loader = JSONLLoader()
        record = loader.get_record_at_index(str(filepath), 1)
        assert record["id"] == 1

    def test_json_get_record_at_index(self, tmp_path):
        """JSON loader should get record by index."""
        filepath = tmp_path / "data.json"
        filepath.write_text('[{"id": 0}, {"id": 1}, {"id": 2}]')

        loader = JSONLoader()
        record = loader.get_record_at_index(str(filepath), 2)
        assert record["id"] == 2

    def test_jsonl_index_out_of_range(self, tmp_path):
        """JSONL loader should raise IndexError for out of range."""
        filepath = tmp_path / "data.jsonl"
        filepath.write_text('{"id": 0}\n{"id": 1}\n')

        loader = JSONLLoader()
        with pytest.raises(IndexError):
            loader.get_record_at_index(str(filepath), 10)

    def test_json_index_out_of_range(self, tmp_path):
        """JSON loader should raise IndexError for out of range."""
        filepath = tmp_path / "data.json"
        filepath.write_text('[{"id": 0}]')

        loader = JSONLoader()
        with pytest.raises(IndexError):
            loader.get_record_at_index(str(filepath), 5)
