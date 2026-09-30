"""Directional flow-factor lookup and iteration for specific grades."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

from calculations.exceptions import CalculationDataError, CalculationInputError
from calculations.heavy_vehicles import calculate_heavy_vehicle_factor

Purpose = Literal["ats", "ptsf"]
FlowBand = Literal["0-300", ">300-600", ">600"]
MAX_FLOW_ITERATIONS = 10  # software guard; the HCM does not prescribe an iteration count


@dataclass(frozen=True)
class FlowIteration:
    """One auditable iteration of a directional passenger-car flow rate."""

    iteration: int
    assumed_flow_pc_per_h: float
    selected_flow_band: str
    grade_factor: float
    truck_equivalency: float
    rv_equivalency: float
    heavy_vehicle_factor: float
    calculated_flow_pc_per_h: float


@dataclass(frozen=True)
class DirectionalFlowResult:
    """Stable equivalent flow and factors for one direction and one measure."""

    flow_pc_per_h: float
    flow_band: str
    grade_factor: float
    truck_equivalency: float
    rv_equivalency: float
    heavy_vehicle_factor: float
    crawl_truck_equivalency: float | None
    iterations: tuple[FlowIteration, ...]


def flow_band(flow_pc_per_h: float) -> FlowBand:
    """Map a directional flow rate to the Chapter 20 0-300/600/>600 band."""
    if not isfinite(flow_pc_per_h) or flow_pc_per_h < 0:
        raise CalculationInputError("El flujo direccional debe ser un valor finito no negativo.")
    if flow_pc_per_h <= 300:
        return "0-300"
    if flow_pc_per_h <= 600:
        return ">300-600"
    return ">600"


def calculate_directional_flow(
    *,
    volume_veh_per_h: float,
    peak_hour_factor: float,
    grade_direction: str,
    grade_percent: float,
    grade_length_km: float,
    purpose: Purpose,
    trucks_percent: float,
    rvs_percent: float,
    tables: dict[str, list[dict[str, Any]]],
    use_crawl_equation: bool = False,
    trucks_at_crawl_percent: float | None = None,
    truck_crawl_speed_km_per_h: float | None = None,
    free_flow_speed_km_per_h: float | None = None,
) -> DirectionalFlowResult:
    """Iteratively compute ``vd`` or ``vo`` with purpose-specific HCM factors.

    Directional flow equations 20-12 and 20-13 use each direction's own grade
    and heavy-vehicle adjustments. Specific upgrades use Exhibits 20-13 to
    20-17. Specific downgrades use fG=1.0 and the level-terrain equivalents
    from Exhibits 20-9 and 20-10. Equation 20-14 is limited to ATS on a
    downgrade with trucks at crawl speed.
    """
    if volume_veh_per_h < 0 or not isfinite(volume_veh_per_h):
        raise CalculationInputError("El volumen horario por sentido debe ser finito y no negativo.")
    if not 0 < peak_hour_factor <= 1:
        raise CalculationInputError("PHF debe estar en el intervalo (0, 1].")
    if grade_direction not in {"upgrade", "downgrade"}:
        raise CalculationInputError("La dirección de pendiente debe ser ascenso o descenso.")
    if purpose not in {"ats", "ptsf"}:
        raise CalculationInputError("La medida debe ser ATS o PTSF.")

    initial_flow = volume_veh_per_h / peak_hour_factor
    assumed_flow = initial_flow
    visited_bands: set[str] = set()
    trace: list[FlowIteration] = []

    for iteration in range(1, MAX_FLOW_ITERATIONS + 1):
        band = str(flow_band(assumed_flow))
        if band in visited_bands:
            raise CalculationDataError(
                f"La iteración de {purpose.upper()} entró en un ciclo entre bandas de flujo; "
                "revise las tablas y el dominio de entrada."
            )
        visited_bands.add(band)

        grade_factor, et, er = _grade_and_equivalencies(
            grade_direction=grade_direction,
            grade_percent=grade_percent,
            grade_length_km=grade_length_km,
            purpose=purpose,
            band=band,
            tables=tables,
            flow_pc_per_h=assumed_flow,
        )
        etc: float | None = None
        if use_crawl_equation and purpose == "ats" and grade_direction == "downgrade":
            if trucks_at_crawl_percent is None or truck_crawl_speed_km_per_h is None or free_flow_speed_km_per_h is None:
                raise CalculationInputError(
                    "Para aplicar la ecuación HCM 20-14 faltan la proporción de camiones "
                    "a velocidad de arrastre y la velocidad de arrastre del camión."
                )
            if trucks_percent <= 0:
                raise CalculationInputError(
                    "Se indicó arrastre, pero el porcentaje de camiones en el descenso es cero."
                )
            if not 0 < trucks_at_crawl_percent <= 100:
                raise CalculationInputError(
                    "La proporción de camiones a velocidad de arrastre debe estar en (0, 100] %."
                )
            difference = free_flow_speed_km_per_h - truck_crawl_speed_km_per_h
            etc = lookup_crawl_truck_equivalency(tables["exhibit_20_18"], difference, band)
            fhv = calculate_crawl_heavy_vehicle_factor(
                trucks_percent=trucks_percent,
                trucks_at_crawl_percent=trucks_at_crawl_percent,
                rvs_percent=rvs_percent,
                truck_equivalency=et,
                rv_equivalency=er,
                crawl_truck_equivalency=etc,
            )
        else:
            fhv = calculate_heavy_vehicle_factor(trucks_percent, rvs_percent, et, er)

        calculated_flow = volume_veh_per_h / (peak_hour_factor * grade_factor * fhv)
        trace.append(FlowIteration(
            iteration=iteration,
            assumed_flow_pc_per_h=assumed_flow,
            selected_flow_band=band,
            grade_factor=grade_factor,
            truck_equivalency=et,
            rv_equivalency=er,
            heavy_vehicle_factor=fhv,
            calculated_flow_pc_per_h=calculated_flow,
        ))
        next_band = str(flow_band(calculated_flow))
        if next_band == band:
            return DirectionalFlowResult(
                flow_pc_per_h=calculated_flow,
                flow_band=band,
                grade_factor=grade_factor,
                truck_equivalency=et,
                rv_equivalency=er,
                heavy_vehicle_factor=fhv,
                crawl_truck_equivalency=etc,
                iterations=tuple(trace),
            )
        if next_band in visited_bands:
            raise CalculationDataError(
                f"La iteración de {purpose.upper()} oscila entre bandas {band} y {next_band}; "
                "no se reporta un flujo sin convergencia."
            )
        assumed_flow = calculated_flow

    raise CalculationDataError(
        f"La iteración de {purpose.upper()} no convergió en {MAX_FLOW_ITERATIONS} iteraciones."
    )


def calculate_crawl_heavy_vehicle_factor(
    *,
    trucks_percent: float,
    trucks_at_crawl_percent: float,
    rvs_percent: float,
    truck_equivalency: float,
    rv_equivalency: float,
    crawl_truck_equivalency: float,
) -> float:
    """Evaluate HCM 2000 Chapter 20 Equation 20-14 for downgrade ATS."""
    for label, value in (("camiones", trucks_percent), ("RV", rvs_percent), ("camiones a arrastre", trucks_at_crawl_percent)):
        if not 0 <= value <= 100:
            raise CalculationInputError(f"El porcentaje de {label} debe estar entre 0 y 100%.")
    if trucks_percent + rvs_percent > 100:
        raise CalculationInputError("Camiones y RV no pueden sumar más de 100%.")
    pt = trucks_percent / 100.0
    pr = rvs_percent / 100.0
    ptc = trucks_at_crawl_percent / 100.0
    if ptc > 0 and pt == 0:
        raise CalculationInputError("PTC no puede ser positivo si no hay camiones en el sentido descendente.")
    denominator = (
        1.0
        + ptc * pt * (crawl_truck_equivalency - 1.0)
        + (1.0 - ptc) * pt * (truck_equivalency - 1.0)
        + pr * (rv_equivalency - 1.0)
    )
    if denominator <= 0 or not isfinite(denominator):
        raise CalculationInputError("La ecuación HCM 20-14 produjo un denominador no válido.")
    return 1.0 / denominator


def _grade_and_equivalencies(
    *, grade_direction: str, grade_percent: float, grade_length_km: float,
    purpose: Purpose, band: str, tables: dict[str, list[dict[str, Any]]],
    flow_pc_per_h: float,
) -> tuple[float, float, float]:
    if grade_direction == "upgrade":
        if purpose == "ats":
            fg_table, et_table, er_table = "exhibit_20_13", "exhibit_20_15", "exhibit_20_17"
        else:
            fg_table, et_table, er_table = "exhibit_20_14", "exhibit_20_16", None
        fg = lookup_upgrade_value(tables[fg_table], grade_percent, grade_length_km, band, "fG")
        et = lookup_upgrade_value(tables[et_table], grade_percent, grade_length_km, band, "ET")
        er = (
            lookup_upgrade_value(tables[er_table], grade_percent, grade_length_km, band, "ER")
            if er_table else lookup_upgrade_value(tables[et_table], grade_percent, grade_length_km, band, "ER")
        )
        return fg, et, er

    fg = _downgrade_grade_factor(tables["specific_downgrade_fG"])
    et_table_id = "tabla_20_9_equivalentes_velocidad" if purpose == "ats" else "tabla_20_10_equivalentes_ptsf"
    er_table_id = et_table_id
    et = lookup_level_equivalency(tables[et_table_id], "Camiones", band)
    er = lookup_level_equivalency(tables[er_table_id], "VR", band)
    return fg, et, er


def lookup_upgrade_value(
    records: list[dict[str, Any]], grade_percent: float, grade_length_km: float,
    band: str, parameter: str,
) -> float:
    """Look up an upgrade table value, interpolating only along grade length."""
    matching_grade = [
        row for row in records
        if float(row["grade_min_pct"]) <= grade_percent
        and (row.get("grade_max_pct", "") == "" or grade_percent < float(row["grade_max_pct"]))
    ]
    if not matching_grade:
        raise CalculationInputError(f"Exhibit no contiene pendiente de {grade_percent:g} %.")
    grade_rows = [row for row in matching_grade if row["directional_flow_range_pcph"] == band]
    lengths = sorted({float(row["grade_length_km"]) for row in grade_rows})
    if not lengths:
        raise CalculationDataError(f"No hay filas de tabla para la banda direccional {band}.")
    if grade_length_km < lengths[0]:
        raise CalculationInputError(
            f"La longitud de pendiente {grade_length_km:g} km queda por debajo del mínimo tabulado {lengths[0]:g} km."
        )
    length = min(grade_length_km, lengths[-1])
    low, high = _bracket(lengths, length)
    values = {}
    for row in grade_rows:
        values[float(row["grade_length_km"])] = float(row[parameter])
    return _linear(length, low, high, values[low], values[high])


def lookup_level_equivalency(
    records: list[dict[str, Any]], vehicle_type: str, band: str,
) -> float:
    """Retrieve an Exhibit 20-9/20-10 level-terrain directional equivalent."""
    row_band = {"0-300": "0-300", ">300-600": ">300-600", ">600": ">600"}[band]
    matches = [
        row for row in records
        if row.get("vehicle_type") == vehicle_type
        and row.get("terrain") in {"Plano", "Nivel"}
        and row.get("directional_flow_pcph_range") == row_band
    ]
    if len(matches) != 1:
        raise CalculationDataError(
            f"Se esperaba un valor único de {vehicle_type} para terreno nivel y banda {band}; "
            f"se encontraron {len(matches)}."
        )
    return float(matches[0]["equivalent"])


def lookup_crawl_truck_equivalency(
    records: list[dict[str, Any]], ffs_minus_crawl_speed_km_per_h: float, band: str,
) -> float:
    """Interpolate Exhibit 20-18 by FFS-crawl-speed difference."""
    if ffs_minus_crawl_speed_km_per_h <= 0 or not isfinite(ffs_minus_crawl_speed_km_per_h):
        raise CalculationInputError("La FFS del descenso debe ser mayor que la velocidad de arrastre del camión.")
    selected = [row for row in records if row["directional_flow_range_pcph"] == band]
    coords = sorted({float(row["ffs_minus_crawl_speed_kmh_min"]) for row in selected})
    values = {float(row["ffs_minus_crawl_speed_kmh_min"]): float(row["ETC"]) for row in selected}
    if not coords:
        raise CalculationDataError(f"Exhibit 20-18 no tiene filas para la banda {band}.")
    difference = max(coords[0], min(ffs_minus_crawl_speed_km_per_h, coords[-1]))
    low, high = _bracket(coords, difference)
    return _linear(difference, low, high, values[low], values[high])


def _downgrade_grade_factor(records: list[dict[str, Any]]) -> float:
    matches = [row for row in records if row.get("parameter") == "fG"]
    if len(matches) != 1:
        raise CalculationDataError("No existe un fG único verificado para el descenso específico.")
    return float(matches[0]["value"])


def _bracket(values: list[float], value: float) -> tuple[float, float]:
    if value in values:
        return value, value
    for lower, upper in zip(values, values[1:]):
        if lower < value < upper:
            return lower, upper
    raise CalculationInputError(f"No se pudo encontrar el intervalo tabulado que contiene {value:g}.")


def _linear(value: float, lower: float, upper: float, lower_value: float, upper_value: float) -> float:
    if lower == upper:
        return lower_value
    return lower_value + (value - lower) / (upper - lower) * (upper_value - lower_value)
