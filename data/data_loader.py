"""Load and query versioned HCM data stored as CSV or JSON files.

Table values remain outside mathematical calculation code. This module handles
catalog metadata, file loading, exact record lookup, and data availability errors.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class DataLoaderError(Exception):
    """Base exception for catalog, file, and lookup failures."""


class DataValidationError(DataLoaderError):
    """Raised when a registry entry or data file has an invalid structure."""


class TableNotFoundError(DataLoaderError):
    """Raised when a requested table identifier is absent from the registry."""


class TableNotAvailableError(DataLoaderError):
    """Raised when a registered table is explicitly pending or unavailable."""


class TableNotVerifiedError(DataLoaderError):
    """Raised when a table is loadable but not approved for parameter lookup."""


class ParameterNotFoundError(DataLoaderError):
    """Raised when a requested lookup has no matching record or parameter."""


class AmbiguousRecordError(DataLoaderError):
    """Raised when lookup criteria match more than one record."""


@dataclass(frozen=True)
class TableDefinition:
    """Documented metadata and file reference for one registered table."""

    id: str
    status: str
    category: str
    source_type: str
    verification_status: str
    source_document: str
    name: str
    source: str
    chapter_section: str
    description: str
    units: str | dict[str, str]
    variables: tuple[str, ...]
    version: str
    observations: str
    file: str | None

    @classmethod
    def from_mapping(cls, item: Mapping[str, Any]) -> "TableDefinition":
        """Validate and construct metadata from a registry object."""
        required_text = (
            "id",
            "status",
            "category",
            "source_type",
            "verification_status",
            "source_document",
            "name",
            "source",
            "chapter_section",
            "description",
            "version",
            "observations",
        )
        for field in required_text:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise DataValidationError(
                    f"Metadato '{field}' obligatorio y debe ser texto no vacío."
                )

        if item["status"] not in {"available", "pending"}:
            raise DataValidationError(
                f"Estado no válido para la tabla '{item['id']}': {item['status']!r}. "
                "Use 'available' o 'pending'."
            )
        valid_verification_statuses = {
            "pending",
            "secondary_source_unverified",
            "reference_only",
            "primary_source_verified",
        }
        if item["verification_status"] not in valid_verification_statuses:
            raise DataValidationError(
                f"Estado de verificación no válido para '{item['id']}': "
                f"{item['verification_status']!r}."
            )
        if item["category"] not in {
            "lookup_table",
            "classification_criteria",
            "capacity_reference",
            "formula_reference",
        }:
            raise DataValidationError(
                f"Categoría no válida para la tabla '{item['id']}': {item['category']!r}."
            )
        file_value = item.get("file")
        if item["status"] == "available" and (
            not isinstance(file_value, str) or not file_value.strip()
        ):
            raise DataValidationError(
                f"La tabla '{item['id']}' está disponible, pero no declara un archivo."
            )
        if item["status"] == "pending" and item.get("file") not in (None, ""):
            raise DataValidationError(
                f"La tabla pendiente '{item['id']}' no debe apuntar a un archivo de datos."
            )

        units = item.get("units")
        if not isinstance(units, str) and not (
            isinstance(units, dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in units.items())
        ):
            raise DataValidationError(
                f"Metadato 'units' no válido para la tabla '{item['id']}'."
            )
        variables = item.get("variables")
        if not isinstance(variables, list) or not all(
            isinstance(variable, str) for variable in variables
        ):
            raise DataValidationError(
                f"Metadato 'variables' debe ser una lista de textos para '{item['id']}'."
            )

        return cls(
            id=item["id"],
            status=item["status"],
            category=item["category"],
            source_type=item["source_type"],
            verification_status=item["verification_status"],
            source_document=item["source_document"],
            name=item["name"],
            source=item["source"],
            chapter_section=item["chapter_section"],
            description=item["description"],
            units=units,
            variables=tuple(variables),
            version=item["version"],
            observations=item["observations"],
            file=item.get("file"),
        )


class DataLoader:
    """Access a data directory containing ``hcm_tables/registry.json``.

    Args:
        data_dir: Project's ``data`` directory. Defaults to this package folder.
    """

    REGISTRY_RELATIVE_PATH = Path("hcm_tables") / "registry.json"

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = (
            Path(data_dir).resolve()
            if data_dir is not None
            else Path(__file__).resolve().parent
        )
        self.tables_dir = (self.data_dir / "hcm_tables").resolve()
        self.registry_path = self.data_dir / self.REGISTRY_RELATIVE_PATH

    def list_tables(self, include_pending: bool = True) -> list[TableDefinition]:
        """Return documented table definitions, optionally excluding pending ones."""
        definitions = self._read_registry()
        if include_pending:
            return definitions
        return [definition for definition in definitions if definition.status == "available"]

    def get_table_metadata(self, table_id: str) -> TableDefinition:
        """Return metadata for an identifier or raise a clear not-found error."""
        for definition in self._read_registry():
            if definition.id == table_id:
                return definition
        raise TableNotFoundError(
            f"No existe la tabla '{table_id}' en el registro "
            f"'{self.registry_path}'."
        )

    def load_table(
        self, table_id: str, *, allow_unverified: bool = False
    ) -> list[dict[str, Any]]:
        """Load a table; unverified data require explicit review-only opt-in."""
        definition = self.get_table_metadata(table_id)
        if definition.status == "pending":
            raise TableNotAvailableError(
                f"La tabla '{table_id}' está pendiente y no contiene datos utilizables. "
                f"{definition.observations}"
            )
        self._require_review_approval(definition, allow_unverified)
        if definition.file is None:
            raise DataValidationError(
                f"La tabla '{table_id}' está marcada disponible, pero no tiene archivo."
            )

        file_path = self._resolve_table_file(definition.file, table_id)
        if not file_path.is_file():
            raise DataValidationError(
                f"No se encontró el archivo de la tabla '{table_id}': '{file_path}'."
            )

        suffix = file_path.suffix.lower()
        try:
            if suffix == ".csv":
                records = self._read_csv(file_path, table_id)
            elif suffix == ".json":
                records = self._read_json(file_path, table_id)
            else:
                raise DataValidationError(
                    f"Formato no admitido para '{table_id}': '{suffix}'. Use CSV o JSON."
                )
        except (OSError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
            raise DataValidationError(
                f"No se pudo leer la tabla '{table_id}' desde '{file_path}': {exc}"
            ) from exc

        if not records:
            raise DataValidationError(
                f"El archivo de la tabla '{table_id}' no contiene registros."
            )
        return records

    def search_records(
        self,
        table_id: str,
        criteria: Mapping[str, Any],
        *,
        allow_unverified: bool = False,
    ) -> list[dict[str, Any]]:
        """Return exact matches; unverified files require explicit review-only opt-in."""
        records = self.load_table(table_id, allow_unverified=allow_unverified)
        available_fields = {field for record in records for field in record}
        unknown_fields = set(criteria) - available_fields
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise DataValidationError(
                f"Campo(s) de búsqueda no presente(s) en '{table_id}': {names}."
            )
        return [
            record
            for record in records
            if all(record.get(field) == expected for field, expected in criteria.items())
        ]

    def get_parameter(
        self,
        table_id: str,
        criteria: Mapping[str, Any],
        parameter: str,
        *,
        allow_unverified: bool = False,
    ) -> Any:
        """Return one parameter from a unique record that passes source review."""
        matches = self.search_records(
            table_id, criteria, allow_unverified=allow_unverified
        )
        if not matches:
            raise ParameterNotFoundError(
                f"No se encontró un registro de '{table_id}' para los criterios {dict(criteria)!r}."
            )
        if len(matches) > 1:
            raise AmbiguousRecordError(
                f"Los criterios {dict(criteria)!r} coinciden con {len(matches)} registros "
                f"de '{table_id}'; agregue criterios para identificar uno solo."
            )
        if parameter not in matches[0]:
            raise ParameterNotFoundError(
                f"El parámetro '{parameter}' no existe en los registros de '{table_id}'."
            )
        return matches[0][parameter]

    def validate_table(self, table_id: str) -> None:
        """Check technical readability, not HCM/source correctness, of a table."""
        self.load_table(table_id, allow_unverified=True)

    def validate_all(self) -> None:
        """Validate the registry and every table marked available."""
        for definition in self._read_registry():
            if definition.status == "available":
                self.load_table(definition.id, allow_unverified=True)

    @staticmethod
    def _require_review_approval(
        definition: TableDefinition, allow_unverified: bool
    ) -> None:
        """Block normative parameter lookups until primary-source review."""
        if (
            definition.verification_status != "primary_source_verified"
            and not allow_unverified
        ):
            raise TableNotVerifiedError(
                f"La tabla '{definition.id}' está almacenada, pero su fuente no ha sido "
                f"verificada contra el HCM 2000 autorizado "
                f"(estado: {definition.verification_status}). Para inspección manual, "
                "solicite allow_unverified=True; no use esos datos para cálculos."
            )

    def _read_registry(self) -> list[TableDefinition]:
        if not self.registry_path.is_file():
            raise DataValidationError(
                f"No se encontró el registro de tablas: '{self.registry_path}'."
            )
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DataValidationError(
                f"No se pudo leer el registro de tablas '{self.registry_path}': {exc}"
            ) from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise DataValidationError(
                f"Registro '{self.registry_path}' debe ser un objeto JSON con schema_version 1."
            )
        items = payload.get("tables")
        if not isinstance(items, list):
            raise DataValidationError(
                f"El campo 'tables' debe ser una lista en '{self.registry_path}'."
            )
        definitions: list[TableDefinition] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise DataValidationError(
                    f"La entrada de tabla en posición {index} debe ser un objeto JSON."
                )
            definition = TableDefinition.from_mapping(item)
            if definition.id in seen_ids:
                raise DataValidationError(
                    f"Identificador de tabla duplicado en el registro: '{definition.id}'."
                )
            seen_ids.add(definition.id)
            definitions.append(definition)
        return definitions

    def _resolve_table_file(self, relative_file: str, table_id: str) -> Path:
        candidate = Path(relative_file)
        if candidate.is_absolute():
            raise DataValidationError(
                f"La ruta del archivo de '{table_id}' debe ser relativa a hcm_tables/."
            )
        resolved = (self.tables_dir / candidate).resolve()
        if not resolved.is_relative_to(self.tables_dir):
            raise DataValidationError(
                f"La ruta del archivo de '{table_id}' debe permanecer dentro de hcm_tables/."
            )
        return resolved

    @staticmethod
    def _read_csv(file_path: Path, table_id: str) -> list[dict[str, Any]]:
        with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames or any(not field for field in reader.fieldnames):
                raise DataValidationError(
                    f"El CSV de '{table_id}' necesita encabezados no vacíos."
                )
            return [dict(row) for row in reader]

    @staticmethod
    def _read_json(file_path: Path, table_id: str) -> list[dict[str, Any]]:
        payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
        records = payload.get("records") if isinstance(payload, dict) else payload
        if not isinstance(records, list) or not all(
            isinstance(record, dict) for record in records
        ):
            raise DataValidationError(
                f"El JSON de '{table_id}' debe ser un arreglo de objetos o contener 'records'."
            )
        return [dict(record) for record in records]
