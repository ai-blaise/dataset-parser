"""Tests for CSVLoader in scripts/data_formats/csv_loader.py."""

from __future__ import annotations

import csv
import pytest

from scripts.data_formats import CSVLoader
from scripts.data_formats.format_detector import detect_format, get_loader, get_loader_for_format


class TestCSVLoaderProperties:
  """Tests for CSVLoader properties."""

  def test_format_name(self):
    loader = CSVLoader()
    assert loader.format_name == "csv"

  def test_supported_extensions(self):
    loader = CSVLoader()
    assert ".csv" in loader.supported_extensions


class TestCSVLoaderLoad:
  """Tests for CSVLoader.load() streaming."""

  def test_load_basic(self, tmp_path):
    filepath = tmp_path / "basic.csv"
    filepath.write_text("prompt,completion\nHello,World\nFoo,Bar\n")

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert len(records) == 2
    assert records[0] == {"prompt": "Hello", "completion": "World"}
    assert records[1] == {"prompt": "Foo", "completion": "Bar"}

  def test_load_returns_generator(self, tmp_path):
    filepath = tmp_path / "gen.csv"
    filepath.write_text("a,b\n1,2\n")

    loader = CSVLoader()
    result = loader.load(str(filepath))
    assert hasattr(result, "__iter__")
    assert hasattr(result, "__next__")

  def test_load_preserves_order(self, tmp_path):
    filepath = tmp_path / "ordered.csv"
    filepath.write_text("value\nfirst\nsecond\nthird\n")

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert records[0]["value"] == "first"
    assert records[1]["value"] == "second"
    assert records[2]["value"] == "third"

  def test_load_quoted_fields(self, tmp_path):
    filepath = tmp_path / "quoted.csv"
    filepath.write_text('name,desc\n"Alice","Has a, comma"\n"Bob","Has ""quotes"""\n')

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert records[0]["desc"] == "Has a, comma"
    assert records[1]["desc"] == 'Has "quotes"'

  def test_load_multiline_fields(self, tmp_path):
    filepath = tmp_path / "multiline.csv"
    filepath.write_text('prompt,completion\n"line1\nline2","response"\n')

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert records[0]["prompt"] == "line1\nline2"

  def test_load_file_not_found(self):
    loader = CSVLoader()
    with pytest.raises(FileNotFoundError):
      list(loader.load("/nonexistent/path/data.csv"))

  def test_load_can_iterate_multiple_times(self, tmp_path):
    filepath = tmp_path / "multi.csv"
    filepath.write_text("id\n1\n2\n3\n")

    loader = CSVLoader()
    first = list(loader.load(str(filepath)))
    second = list(loader.load(str(filepath)))
    assert first == second


class TestCSVLoaderLoadAll:
  """Tests for CSVLoader.load_all()."""

  def test_load_all_records(self, tmp_path):
    filepath = tmp_path / "all.csv"
    lines = ["id"] + [str(i) for i in range(10)]
    filepath.write_text("\n".join(lines) + "\n")

    loader = CSVLoader()
    records = loader.load_all(str(filepath))
    assert len(records) == 10

  def test_load_all_with_max_records(self, tmp_path):
    filepath = tmp_path / "limited.csv"
    lines = ["id"] + [str(i) for i in range(100)]
    filepath.write_text("\n".join(lines) + "\n")

    loader = CSVLoader()
    records = loader.load_all(str(filepath), max_records=5)
    assert len(records) == 5
    assert records[0]["id"] == "0"

  def test_load_all_max_records_exceeds_total(self, tmp_path):
    filepath = tmp_path / "small.csv"
    filepath.write_text("id\n1\n2\n3\n")

    loader = CSVLoader()
    records = loader.load_all(str(filepath), max_records=100)
    assert len(records) == 3

  def test_load_all_with_progress_callback(self, tmp_path):
    filepath = tmp_path / "progress.csv"
    lines = ["id"] + [str(i) for i in range(5)]
    filepath.write_text("\n".join(lines) + "\n")

    callback_calls = []
    def progress_callback(loaded: int, total: int | None) -> None:
      callback_calls.append((loaded, total))

    loader = CSVLoader()
    loader.load_all(str(filepath), progress_callback=progress_callback)

    assert len(callback_calls) >= 1
    assert callback_calls[-1][0] == 5


class TestCSVLoaderGetRecordCount:
  """Tests for CSVLoader.get_record_count()."""

  def test_count_basic(self, tmp_path):
    filepath = tmp_path / "count.csv"
    filepath.write_text("a,b\n1,2\n3,4\n5,6\n")

    loader = CSVLoader()
    assert loader.get_record_count(str(filepath)) == 3

  def test_count_header_only(self, tmp_path):
    filepath = tmp_path / "header_only.csv"
    filepath.write_text("prompt,completion\n")

    loader = CSVLoader()
    assert loader.get_record_count(str(filepath)) == 0

  def test_count_skips_empty_lines(self, tmp_path):
    filepath = tmp_path / "empties.csv"
    filepath.write_text("id\n1\n\n2\n\n3\n")

    loader = CSVLoader()
    assert loader.get_record_count(str(filepath)) == 3


class TestCSVLoaderGetRecordAtIndex:
  """Tests for CSVLoader.get_record_at_index()."""

  def test_get_first_record(self, tmp_path):
    filepath = tmp_path / "first.csv"
    filepath.write_text("id,name\n0,Alice\n1,Bob\n2,Charlie\n")

    loader = CSVLoader()
    record = loader.get_record_at_index(str(filepath), 0)
    assert record["name"] == "Alice"

  def test_get_last_record(self, tmp_path):
    filepath = tmp_path / "last.csv"
    filepath.write_text("id,name\n0,Alice\n1,Bob\n2,Charlie\n")

    loader = CSVLoader()
    record = loader.get_record_at_index(str(filepath), 2)
    assert record["name"] == "Charlie"

  def test_negative_index_raises(self, tmp_path):
    filepath = tmp_path / "neg.csv"
    filepath.write_text("id\n1\n")

    loader = CSVLoader()
    with pytest.raises(IndexError):
      loader.get_record_at_index(str(filepath), -1)

  def test_out_of_range_raises(self, tmp_path):
    filepath = tmp_path / "oor.csv"
    filepath.write_text("id\n1\n2\n")

    loader = CSVLoader()
    with pytest.raises(IndexError):
      loader.get_record_at_index(str(filepath), 10)


class TestCSVLoaderLargeFields:
  """Tests for handling large fields (up to 124K chars)."""

  def test_large_completion_field(self, tmp_path):
    filepath = tmp_path / "large.csv"
    large_text = "x" * 130_000  # 130K chars, exceeds 124K requirement
    with open(str(filepath), "w", newline="") as f:
      writer = csv.writer(f)
      writer.writerow(["prompt", "completion"])
      writer.writerow(["test prompt", large_text])

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert len(records) == 1
    assert len(records[0]["completion"]) == 130_000


class TestCSVLoaderEdgeCases:
  """Tests for edge cases."""

  def test_unicode_content(self, tmp_path):
    filepath = tmp_path / "unicode.csv"
    filepath.write_text("text\n世界\n🎉\nhéllo\n", encoding="utf-8")

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert records[0]["text"] == "世界"
    assert records[1]["text"] == "🎉"
    assert records[2]["text"] == "héllo"

  def test_single_column(self, tmp_path):
    filepath = tmp_path / "single_col.csv"
    filepath.write_text("value\none\ntwo\n")

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert len(records) == 2
    assert records[0] == {"value": "one"}

  def test_many_columns(self, tmp_path):
    filepath = tmp_path / "wide.csv"
    headers = ",".join([f"col{i}" for i in range(20)])
    values = ",".join([str(i) for i in range(20)])
    filepath.write_text(f"{headers}\n{values}\n")

    loader = CSVLoader()
    records = list(loader.load(str(filepath)))
    assert len(records) == 1
    assert records[0]["col0"] == "0"
    assert records[0]["col19"] == "19"


class TestCSVFormatDetection:
  """Tests for CSV in the format detection system."""

  def test_detect_csv_extension(self):
    assert detect_format("data.csv") == "csv"

  def test_get_loader_returns_csv_loader(self, tmp_path):
    filepath = tmp_path / "test.csv"
    filepath.write_text("a\n1\n")

    loader = get_loader(str(filepath))
    assert loader.format_name == "csv"

  def test_get_loader_for_format_csv(self):
    loader = get_loader_for_format("csv")
    assert loader.format_name == "csv"
