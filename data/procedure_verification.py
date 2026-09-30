"""Availability verification for HCM tables required by the two-way module."""

from typing import Any
import json
from pathlib import Path

from data.data_loader import DataLoader, DataLoaderError


REQUIRED_TWO_LANE_TABLES = (
    ("tabla_20_5_fls", "Ajuste por ancho de carril y berma (Exhibit 20-5)"),
    ("tabla_20_6_fa", "Ajuste por densidad de accesos (Exhibit 20-6)"),
    ("tabla_20_7_fg_velocidad", "Factor fG para ATS (Exhibit 20-7)"),
    ("tabla_20_8_fg_ptsf", "Factor fG para PTSF (Exhibit 20-8)"),
    ("tabla_20_9_equivalentes_velocidad", "Equivalencias para ATS (Exhibit 20-9)"),
    ("tabla_20_10_equivalentes_ptsf", "Equivalencias para PTSF (Exhibit 20-10)"),
    ("tabla_20_11_fnp", "Ajuste fnp (Exhibit 20-11)"),
    ("tabla_20_12_fd_np", "Ajuste fd/np (Exhibit 20-12)"),
    ("los_carreteras_dos_carriles", "Criterios LOS (Exhibits 20-2 y 20-4)"),
    ("capacidad_dos_carriles_reference", "Capacidad bidireccional y por sentido"),
)


def verify_two_lane_tables(
    data_loader: DataLoader | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Load each required primary-source-verified table and report its status.

    A successful table check means the table is available and primary-source
    verified. It does not prove that a selected row matches the current inputs;
    that lookup is confirmed by successful completion of the HCM calculation.
    """
    loader = data_loader or DataLoader()
    results: list[dict[str, Any]] = []
    all_verified = True
    for table_id, label in REQUIRED_TWO_LANE_TABLES:
        try:
            definition = loader.get_table_metadata(table_id)
            records = loader.load_table(table_id)
            results.append({
                "Parámetro/tabla": label,
                "Estado": "Disponible y verificada",
                "Registros": len(records),
                "Fuente": definition.chapter_section,
                "Detalle": "",
            })
        except DataLoaderError as exc:
            all_verified = False
            results.append({
                "Parámetro/tabla": label,
                "Estado": "No disponible o no verificada",
                "Registros": 0,
                "Fuente": "",
                "Detalle": str(exc),
            })
    return results, all_verified


def verify_multilane_tables() -> tuple[list[dict[str, Any]], bool]:
    """Check the supplied secondary-source multilane table file is readable."""
    path = Path(__file__).resolve().parent / "hcm_tables" / "reviewed" / "multilane_design_tables.json"
    label = "Tablas multicarril (ajustes, equivalencias y criterios LOS)"
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        rows = sum(len(value) for key, value in data.items() if isinstance(value, list))
        rows += sum(len(value) for key, value in data.get("level_of_service_criteria", {}).items())
        return ([{
            "Parámetro/tabla": label,
            "Estado": "Disponible; fuente secundaria pendiente de cotejo con HCM original",
            "Registros": rows,
            "Fuente": data["metadata"]["source"],
            "Detalle": "Se identifica explícitamente la procedencia secundaria en resultados/advertencias.",
        }], True)
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return ([{
            "Parámetro/tabla": label,
            "Estado": "No disponible",
            "Registros": 0,
            "Fuente": str(path),
            "Detalle": str(exc),
        }], False)
