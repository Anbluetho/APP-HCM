"""Synthetic tests for the generic data loader; values are not HCM data."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from data.data_loader import (
    AmbiguousRecordError,
    DataLoader,
    DataValidationError,
    ParameterNotFoundError,
    TableNotAvailableError,
    TableNotFoundError,
    TableNotVerifiedError,
)


class DataLoaderTests(unittest.TestCase):
    """Exercise file loading and lookup using temporary synthetic fixtures."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.tables_dir = self.data_dir / "hcm_tables"
        self.tables_dir.mkdir(parents=True)
        self.loader = DataLoader(self.data_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_registry(self, tables: list[dict[str, Any]]) -> None:
        registry = {"schema_version": 1, "tables": tables}
        (self.tables_dir / "registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )

    @staticmethod
    def _table_definition(
        table_id: str, filename: str, status: str = "available"
    ) -> dict[str, Any]:
        return {
            "id": table_id,
            "status": status,
            "category": "lookup_table",
            "source_type": "synthetic_test_fixture",
            "verification_status": "pending" if status == "pending" else "secondary_source_unverified",
            "source_document": "synthetic test fixture",
            "name": f"Synthetic fixture {table_id}",
            "source": "Test fixture only; not an HCM source",
            "chapter_section": "Synthetic test section",
            "description": "Synthetic records to verify generic loading behavior.",
            "units": {"code": "label", "value": "synthetic unit"},
            "variables": ["code"],
            "version": "test fixture",
            "observations": "Not real engineering or HCM values.",
            "file": filename if status == "available" else None,
        }

    def test_load_csv_and_search_records(self) -> None:
        (self.tables_dir / "fixture.csv").write_text(
            "code,value\nA,synthetic-alpha\nB,synthetic-beta\n", encoding="utf-8"
        )
        self._write_registry([self._table_definition("fixture", "fixture.csv")])

        rows = self.loader.load_table("fixture", allow_unverified=True)
        matches = self.loader.search_records(
            "fixture", {"code": "B"}, allow_unverified=True
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(matches, [{"code": "B", "value": "synthetic-beta"}])

    def test_load_json_and_get_parameter(self) -> None:
        (self.tables_dir / "fixture.json").write_text(
            json.dumps({"records": [{"key": "synthetic-key", "value": "synthetic-json-value"}]}),
            encoding="utf-8",
        )
        self._write_registry([self._table_definition("fixture", "fixture.json")])

        value = self.loader.get_parameter(
            "fixture", {"key": "synthetic-key"}, "value", allow_unverified=True
        )

        self.assertEqual(value, "synthetic-json-value")
        self.loader.validate_table("fixture")
        self.loader.validate_all()

    def test_unknown_table_raises_clear_error(self) -> None:
        self._write_registry([])
        with self.assertRaisesRegex(TableNotFoundError, "No existe la tabla"):
            self.loader.load_table("missing")

    def test_project_registry_exposes_reviewed_tables_and_reference_formulas(self) -> None:
        project_loader = DataLoader()
        definitions = project_loader.list_tables()

        imported = [item for item in definitions if item.status == "available"]
        pending = [item for item in definitions if item.status == "pending"]
        self.assertEqual(len(imported), 11)
        self.assertEqual(len(pending), 1)
        verified = [item for item in imported if item.verification_status == "primary_source_verified"]
        references = [item for item in imported if item.verification_status == "reference_only"]
        self.assertEqual(len(verified), 10)
        self.assertEqual(len(references), 1)
        self.assertEqual(len(project_loader.list_tables(include_pending=False)), 11)
        # Every approved dataset is loadable by default; formulas remain gated.
        project_loader.validate_all()
        with self.assertRaises(TableNotVerifiedError):
            project_loader.load_table("formulas_hcm_2_carriles_reference")

    def test_reviewed_table_12_uses_manual_flow_labels(self) -> None:
        project_loader = DataLoader()
        records = project_loader.load_table("tabla_20_12_fd_np")
        self.assertEqual(len(records), 192)
        low_rows = [row for row in records if row["vp_pcph"] == "<=200"]
        self.assertEqual(len(low_rows), 30)
        self.assertEqual(
            {row["directional_split"] for row in low_rows},
            {"50/50", "60/40", "70/30", "80/20", "90/10"},
        )

    def test_reviewed_capacity_includes_manual_short_segment_range(self) -> None:
        project_loader = DataLoader()
        rows = project_loader.load_table("capacidad_dos_carriles_reference")
        self.assertEqual(rows[-1], {
            "capacity_type": "short_segment_combined",
            "capacity": "3200-3400",
            "unit": "pc/h",
        })

    def test_pending_table_cannot_be_loaded(self) -> None:
        self._write_registry(
            [self._table_definition("pending", "", status="pending")]
        )
        with self.assertRaisesRegex(TableNotAvailableError, "está pendiente"):
            self.loader.load_table("pending")

    def test_missing_file_raises_clear_error(self) -> None:
        self._write_registry([self._table_definition("fixture", "absent.csv")])
        with self.assertRaisesRegex(DataValidationError, "No se encontró el archivo"):
            self.loader.load_table("fixture", allow_unverified=True)

    def test_missing_parameter_raises_clear_error(self) -> None:
        (self.tables_dir / "fixture.csv").write_text(
            "code,value\nA,synthetic-alpha\n", encoding="utf-8"
        )
        self._write_registry([self._table_definition("fixture", "fixture.csv")])
        with self.assertRaisesRegex(ParameterNotFoundError, "No se encontró un registro"):
            self.loader.get_parameter(
                "fixture", {"code": "unknown"}, "value", allow_unverified=True
            )
        with self.assertRaisesRegex(ParameterNotFoundError, "no existe"):
            self.loader.get_parameter(
                "fixture", {"code": "A"}, "absent", allow_unverified=True
            )

    def test_ambiguous_lookup_is_not_silently_selected(self) -> None:
        (self.tables_dir / "fixture.csv").write_text(
            "group,value\nsame,synthetic-one\nsame,synthetic-two\n", encoding="utf-8"
        )
        self._write_registry([self._table_definition("fixture", "fixture.csv")])
        with self.assertRaisesRegex(AmbiguousRecordError, "coinciden con 2 registros"):
            self.loader.get_parameter(
                "fixture", {"group": "same"}, "value", allow_unverified=True
            )

    def test_file_path_cannot_escape_table_directory(self) -> None:
        self._write_registry([self._table_definition("fixture", "../outside.csv")])
        with self.assertRaisesRegex(DataValidationError, "permanecer dentro"):
            self.loader.load_table("fixture", allow_unverified=True)

    def test_parameter_lookup_requires_primary_source_verification(self) -> None:
        (self.tables_dir / "fixture.json").write_text(
            json.dumps(
                {"records": [{"key": "synthetic-key", "value": "synthetic-value"}]}
            ),
            encoding="utf-8",
        )
        self._write_registry([self._table_definition("fixture", "fixture.json")])

        with self.assertRaisesRegex(TableNotVerifiedError, "no ha sido verificada"):
            self.loader.get_parameter("fixture", {"key": "synthetic-key"}, "value")

        value = self.loader.get_parameter(
            "fixture", {"key": "synthetic-key"}, "value", allow_unverified=True
        )
        self.assertEqual(value, "synthetic-value")


if __name__ == "__main__":
    unittest.main()


