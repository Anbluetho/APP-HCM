"""HCM 2000 multilane general-segment procedure transcribed from the supplied reference.

Tabulated values are loaded from data/hcm_tables/reviewed/multilane_design_tables.json.
The source file is a secondary transcription and its registry explicitly records
that the values still require comparison against the HCM 2000 original.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from math import isfinite
from pathlib import Path
from typing import Any

from calculations.exceptions import CalculationDataError, CalculationInputError
from calculations.heavy_vehicles import calculate_heavy_vehicle_factor
from models.calculation_result import CalculationResult
from models.multilane_highway import MultilaneHighwayInputs


TABLE_PATH = Path(__file__).resolve().parents[1] / "data" / "hcm_tables" / "reviewed" / "multilane_design_tables.json"


def analyze_multilane_segment(inputs: MultilaneHighwayInputs) -> CalculationResult:
    """Calculate FFS, per-lane flow, density and LOS for a multilane segment.

    Source: supplied C05-C07-Capacidad_2.pdf, pp. 18-22, presenting HCM 2000
    Chapter 12 criteria. The reported data provenance remains secondary-source
    unverified pending comparison with the original HCM exhibits.
    """
    _validate(inputs)
    data = _load_tables()
    terrain = data["terrain_equivalencies"].get(inputs.terrain)
    if terrain is None:
        raise CalculationInputError(
            "El documento de referencia no contiene equivalencias para terreno escarpado. "
            "Se requiere la tabla HCM 2000 aplicable antes de calcular ese caso."
        )
    f_ls = _interpolate(
        [(float(row["lane_width_m"]), float(row["reduction_kmh"])) for row in data["lane_width_adjustment"]],
        inputs.lane_width_m,
    )
    lane_clearance_rows = [row for row in data["lateral_clearance_adjustment"] if row["lanes_per_direction"] == inputs.lanes_per_direction]
    f_lc = _interpolate(
        [(float(row["clearance_m"]), float(row["reduction_kmh"])) for row in lane_clearance_rows],
        inputs.lateral_clearance_m,
    )
    f_m = float(data["median_adjustment"][inputs.median_type])
    f_a = _access_adjustment(data["access_adjustment"], inputs.access_points_per_km)
    ffs = inputs.base_free_flow_speed_km_per_h - f_ls - f_lc - f_m - f_a
    if not 70 <= ffs <= 100:
        raise CalculationInputError(
            f"La FFS calculada ({ffs:.2f} km/h) queda fuera del dominio 70-100 km/h de la tabla de criterios multicarril."
        )
    band = str(_ffs_band(ffs))
    if band not in data["level_of_service_criteria"]:
        raise CalculationInputError(
            f"FFS calculada {ffs:.2f} km/h queda fuera de bandas tabuladas (70 a 100 km/h)."
        )

    equivalencies = terrain
    f_hv = calculate_heavy_vehicle_factor(
        inputs.trucks_percent,
        inputs.recreational_vehicles_percent,
        float(equivalencies["truck"]),
        float(equivalencies["recreational_vehicle"]),
    )
    directional_demand = inputs.hourly_volume_two_way_veh_per_h * inputs.major_direction_percent / 100.0
    vp = directional_demand / (
        inputs.peak_hour_factor * inputs.lanes_per_direction * f_hv * inputs.driver_population_factor
    )
    criteria = data["level_of_service_criteria"][band]
    capacity_per_lane = float(criteria["flow_max_pc_per_h_per_lane"]["E"])
    vc = vp / capacity_per_lane
    if vp > capacity_per_lane:
        speed = None
        density = None
        los = "F"
    else:
        speed = _interpolate_operating_speed(
            ffs, vp, criteria, float(data["speed_breakpoint_pc_per_h_per_lane"])
        )
        density = vp / speed if speed > 0 else float("inf")
        los = _classify_density(density, criteria["density_max_pc_per_km_per_lane"])

    return CalculationResult(
        inputs=asdict(inputs),
        parameters={
            "lane_width_adjustment_kmh": f_ls,
            "lateral_clearance_adjustment_kmh": f_lc,
            "median_adjustment_kmh": f_m,
            "access_adjustment_kmh": f_a,
            "truck_equivalency": equivalencies["truck"],
            "recreational_vehicle_equivalency": equivalencies["recreational_vehicle"],
            "heavy_vehicle_factor": f_hv,
            "capacity_pc_per_h_per_lane": capacity_per_lane,
            "source_document": data["metadata"]["source"],
            "source_verification_status": data["metadata"]["verification_status"],
            "criteria_ffs_band_km_per_h": band,
        },
        intermediate_results={
            "free_flow_speed_km_per_h": ffs,
            "directional_volume_veh_per_h": directional_demand,
            "adjusted_flow_pc_per_h_per_lane": vp,
            "operating_speed_km_per_h": speed,
            "density_pc_per_km_per_lane": density,
            "volume_capacity_ratio": vc,
        },
        final_results={
            "capacity_pc_per_h_per_lane": capacity_per_lane,
            "capacity_pc_per_h_direction": capacity_per_lane * inputs.lanes_per_direction,
            "volume_capacity_ratio": vc,
            "average_travel_speed_km_per_h": speed,
            "density_pc_per_km_per_lane": density,
            "level_of_service": los,
            "other_performance_measures": None,
        },
        warnings=(
            "Tablas multicarril transcritas del documento PUCE proporcionado (pp. 18-22); requieren cotejo con el HCM 2000 original.",
            "La velocidad se interpola linealmente entre los puntos de velocidad y flujo máximo de la tabla multicarril del documento de referencia.",
            "El factor de población de conductores fP es una entrada explícita del usuario y debe justificarse con datos del proyecto.",
        ),
        formula_references=(
            "C05-C07-Capacidad_2.pdf, sección 3, Tablas 14-19, pp. 18-22 (transcripción secundaria de HCM 2000, Capítulo 12).",
            "FFS = BFFS - fLW - fLC - fM - fA; flujo por carril = VHD direccional / (PHF × N × fHV × fP); densidad = vp / S.",
        ),
    )


def _load_tables() -> dict[str, Any]:
    try:
        with TABLE_PATH.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise CalculationDataError(f"No se pudo cargar el archivo de tablas multicarril: {exc}") from exc


def _validate(inputs: MultilaneHighwayInputs) -> None:
    numeric = asdict(inputs)
    for key, value in numeric.items():
        if isinstance(value, (int, float)) and not isfinite(value):
            raise CalculationInputError(f"{key} debe ser un valor finito.")
    if inputs.terrain == "escarpado":
        return  # Raise a specific missing-table warning before doing any lookup.
    if inputs.terrain not in {"plano", "ondulado", "montanoso"}:
        raise CalculationInputError("Terreno multicarril fuera de las categorías documentadas.")
    if inputs.hourly_volume_two_way_veh_per_h <= 0:
        raise CalculationInputError("El volumen horario debe ser mayor que cero.")
    if not 0 < inputs.peak_hour_factor <= 1:
        raise CalculationInputError("PHF debe estar en (0, 1].")
    if inputs.major_direction_percent not in {50, 60, 70, 80, 90}:
        raise CalculationInputError("DIR debe corresponder a una opción documentada entre 50/50 y 90/10.")
    if inputs.lanes_per_direction not in {2, 3}:
        raise CalculationInputError("La tabla de despeje lateral documenta 2 o 3 carriles por sentido.")
    if not 3.0 <= inputs.lane_width_m <= 3.6:
        raise CalculationInputError("El ancho de carril multicarril debe estar entre 3,0 y 3,6 m según la tabla transcrita.")
    if not 0 <= inputs.lateral_clearance_m <= 3.6:
        raise CalculationInputError("El despeje lateral total debe estar entre 0 y 3,6 m.")
    if inputs.median_type not in {"divided", "undivided"}:
        raise CalculationInputError("Seleccione mediana dividida o vía no dividida.")
    if inputs.trucks_percent < 0 or inputs.recreational_vehicles_percent < 0 or inputs.trucks_percent + inputs.recreational_vehicles_percent > 100:
        raise CalculationInputError("Los porcentajes de pesados/RV deben ser no negativos y sumar como máximo 100%.")
    if inputs.driver_population_factor not in {0.85, 0.9, 0.95, 1.0}:
        raise CalculationInputError("fP debe ser uno de los valores indicados en el documento: 0,85; 0,90; 0,95 o 1,00.")
    if inputs.access_points_per_km not in {0, 6, 12, 18} and inputs.access_points_per_km < 24:
        raise CalculationInputError("La tabla de accesos usa 0, 6, 12, 18 o ≥24 accesos/km.")
    if not 70 <= inputs.base_free_flow_speed_km_per_h <= 110:
        raise CalculationInputError("BFFS debe estar entre 70 y 110 km/h.")


def _interpolate(points: list[tuple[float, float]], value: float) -> float:
    points = sorted(points)
    if value < points[0][0] or value > points[-1][0]:
        raise CalculationInputError(f"{value} queda fuera del rango tabulado {points[0][0]}–{points[-1][0]}.")
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if value == x0:
            return y0
        if x0 <= value <= x1:
            return y0 + (value - x0) * (y1 - y0) / (x1 - x0)
    return points[-1][1]


def _access_adjustment(rows: list[dict[str, float]], density: float) -> float:
    for row in rows:
        if density == row["accesses_per_km"] or (row["accesses_per_km"] == 24 and density >= 24):
            return float(row["reduction_kmh"])
    raise CalculationInputError("Densidad de accesos fuera de las categorías tabuladas.")


def _ffs_band(ffs: float) -> int:
    for band in (70, 80, 90, 100):
        if ffs <= band:
            return band
    return 110


def _interpolate_operating_speed(
    ffs: float, vp: float, criteria: dict[str, Any], breakpoint: float,
) -> float:
    flows = criteria["flow_max_pc_per_h_per_lane"]
    speeds = criteria["speed_km_per_h"]
    if vp <= breakpoint:
        return ffs
    points = [(breakpoint, float(ffs))]
    points.extend((float(flows[level]), float(speeds[level])) for level in "CDE")
    return _interpolate(points, vp)


def _classify_density(density: float, limits: dict[str, float]) -> str:
    for level in "ABCDE":
        if density <= float(limits[level]):
            return level
    return "F"
