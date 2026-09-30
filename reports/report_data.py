"""Build a presentation-independent, auditable report payload.

The payload is shared by exports such as CSV and a future PDF renderer. It
contains only submitted inputs and values returned by the calculation engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.calculation_result import CalculationResult


APPLICATION_VERSION = "0.5.0"
PROCEDURE_NAME = (
    "HCM 2000, Capítulo 20 — análisis operacional de segmento bidireccional "
    "extendido de carretera de dos carriles"
)


def build_report_payload(
    submitted_inputs: dict[str, Any],
    result: CalculationResult,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Return metadata and labeled records ready for CSV/PDF rendering."""
    now = generated_at or datetime.now().astimezone()
    project = submitted_inputs.get("project", {})
    facility = submitted_inputs.get("facility", {})
    facility_type = facility.get("facility_type", "")
    procedure = (
        "HCM 2000, Capítulo 12 — segmento general de carretera multicarril"
        if facility_type == "Carretera multicarril"
        else PROCEDURE_NAME
    )
    source = (
        "C05-C07-Capacidad_2.pdf, sección 3 (transcripción secundaria de HCM 2000, Capítulo 12)"
        if facility_type == "Carretera multicarril"
        else "Highway Capacity Manual 2000, Chapter 20"
    )
    return {
        "metadata": {
            "project": project.get("project_name", ""),
            "analyst": project.get("analyst", ""),
            "location": project.get("location", ""),
            "data_origin": project.get("data_origin", ""),
            "date": now.isoformat(timespec="seconds"),
            "facility_type": facility.get("facility_type", ""),
            "procedure": procedure,
            "application_version": APPLICATION_VERSION,
            "methodological_source": source,
        },
        "sections": [
            {"name": "Datos de entrada", "records": _input_records(submitted_inputs, result)},
            {"name": "Factores HCM", "records": _flatten("Parámetro HCM", result.parameters)},
            {"name": "Cálculos intermedios", "records": _flatten("Resultado intermedio", result.intermediate_results)},
            {"name": "Resultados finales", "records": _flatten("Resultado", result.final_results)},
            {"name": "Advertencias", "records": [
                _record("Advertencia", f"{i + 1}", warning, "", "Motor HCM")
                for i, warning in enumerate(result.warnings)
            ]},
            {"name": "Referencias", "records": [
                _record("Referencia", f"{i + 1}", reference, "", "HCM 2000")
                for i, reference in enumerate(result.formula_references)
            ]},
        ],
    }


def _input_records(submitted: dict[str, Any], result: CalculationResult) -> list[dict[str, str]]:
    """Include engine inputs and project/observational fields from the form."""
    rows = _flatten("Entrada de cálculo", result.inputs)
    for section in ("project", "facility", "operation", "procedure_additional"):
        fields = submitted.get(section, {})
        for key, value in fields.items():
            if section in {"operation", "procedure_additional"} and key not in {"field_notes"}:
                continue
            rows.append(_record(f"Dato complementario ({section})", key, value, "", "Entrada del usuario; no usada en cálculo"))
    return rows


def _flatten(group: str, values: dict[str, Any], prefix: str = "") -> list[dict[str, str]]:
    """Flatten nested engine values while retaining readable field paths."""
    records: list[dict[str, str]] = []
    for key, value in values.items():
        label = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            records.extend(_flatten(group, value, label))
        elif isinstance(value, (list, tuple)):
            records.append(_record(group, label, "; ".join(map(str, value))))
        else:
            records.append(_record(group, label, value))
    return records


def _record(
    group: str, item: str, value: Any, unit: str = "", source: str = "",
) -> dict[str, str]:
    """Normalize one report record to CSV-friendly strings."""
    return {
        "Sección": group,
        "Dato": item,
        "Valor": "No calculado" if value is None else str(value),
        "Unidad": unit,
        "Fuente": source,
    }
