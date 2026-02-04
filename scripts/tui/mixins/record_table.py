"""
RecordTable Mixin for dynamic schema-aware record display.

Provides reusable methods for:
- Dynamic column generation based on detected schema
- Single-record detection for skip-to-detail behavior
- Consistent record table population

Usage:
    class MyScreen(RecordTableMixin, Screen):
        def _load_records(self, filepath):
            records = load_all_records(filepath)
            mapping = get_field_mapping(filepath)

            if self._should_skip_record_list(records):
                # Go directly to detail view
                self._show_record_detail(records[0])
            else:
                # Show record list
                self._populate_records(table, records, mapping)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import DataTable

from scripts.tui.mixins.data_table import DataTableMixin

if TYPE_CHECKING:
    from scripts.tui.data_loader import FieldMapping


class RecordTableMixin(DataTableMixin):
    """Mixin providing dynamic schema-aware record table functionality.

    Inherits from DataTableMixin for common table operations.
    """

    def _get_record_columns(
        self, mapping: "FieldMapping"
    ) -> list[tuple[str, int | None]]:
        """Generate column config based on detected field mapping.

        Only includes columns for fields that were actually detected.
        This ensures the table adapts to whatever schema the data uses.

        Args:
            mapping: The detected field mapping for the dataset.

        Returns:
            List of (column_name, width) tuples. Width of None means flexible.
        """
        cols: list[tuple[str, int | None]] = [("IDX", 6)]

        if mapping.uuid:
            cols.append(("ID", 15))
        if mapping.messages:
            cols.append(("MSGS", 6))
        if mapping.tools:
            cols.append(("TOOLS", 6))

        cols.append(("PREVIEW", None))  # flexible width
        return cols

    def _build_record_row(
        self, summary: dict[str, Any], mapping: "FieldMapping"
    ) -> list[str]:
        """Build a table row dynamically based on field mapping.

        Only includes values for columns that exist in the mapping.

        Args:
            summary: Record summary from get_record_summary().
            mapping: The detected field mapping for the dataset.

        Returns:
            List of string values for the row.
        """
        row: list[str] = [str(summary["index"])]

        if mapping.uuid:
            row.append(summary["uuid"])
        if mapping.messages:
            row.append(str(summary["msg_count"]))
        if mapping.tools:
            row.append(str(summary["tool_count"]))

        row.append(summary["preview"])
        return row

    def _should_skip_record_list(self, records: list[dict[str, Any]]) -> bool:
        """Check if record list should be skipped.

        When there's only one record, it's more useful to go directly
        to the detail/comparison view rather than showing a list with
        a single item.

        Args:
            records: List of loaded records.

        Returns:
            True if there's exactly one record and list should be skipped.
        """
        return len(records) == 1

    def _populate_record_table(
        self,
        table: DataTable,
        records: list[dict[str, Any]],
        mapping: "FieldMapping",
        get_summary_fn: Any = None,
    ) -> None:
        """Populate a DataTable with records using dynamic columns.

        Clears existing content and adds columns/rows based on the
        detected field mapping.

        Args:
            table: The DataTable widget to populate.
            records: List of records to display.
            mapping: The detected field mapping for the dataset.
            get_summary_fn: Optional custom summary function. If None,
                           uses get_record_summary from data_loader.
        """
        from scripts.tui.data_loader import get_record_summary

        if get_summary_fn is None:
            get_summary_fn = get_record_summary

        # Clear existing content
        table.clear(columns=True)

        # Add columns dynamically using base class method
        columns = self._get_record_columns(mapping)
        self._configure_table(table, columns)

        # Add rows
        for idx, record in enumerate(records):
            summary = get_summary_fn(record, idx, mapping)
            row = self._build_record_row(summary, mapping)
            table.add_row(*row, key=str(idx))

