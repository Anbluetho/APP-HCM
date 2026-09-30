"""HCM 2000 operational analysis for an extended two-way, two-lane segment.

Pure calculation/orchestration module. It has no Streamlit dependency; every
tabulated parameter is retrieved from the verified data registry.
"""

from __future__ import annotations

from dataclasses import asdict
from math import isfinite
import re
from typing import Any, Callable

from calculations.capacity import assess_capacity
from calculations.design_hour_volume import calculate_design_hour_volume
from calculations.exceptions import CalculationDataError, CalculationInputError
from calculations.flow import calculate_equivalent_flow_rate
from calculations.heavy_vehicles import calculate_heavy_vehicle_factor
from calculations.los import classify_level_of_service
from calculations.performance import (
    calculate_average_travel_speed,
    calculate_base_ptsf,
    calculate_other_performance_measures,
    calculate_ptsf,
)
from data.data_loader import DataLoader, DataLoaderError
from models.calculation_result import CalculationResult
from models.two_lane_highway import TwoLaneHighwayInputs


class TwoLaneHighwayAnalyzer:
    """Calculate HCM 2000 two-way-segment LOS and retain an audit trail."""

    FORMULA_REFERENCES = (
        "HCM 2000, Chapter 20, Equations 20-2 through 20-8.",
        "HCM 2000, Chapter 20, Exhibits 20-2 and 20-4 through 20-12.",
        "HCM 2000, Chapter 20, capacity criteria: 1,700 pc/h per direction and 3,200 pc/h two-way.",
        "HCM 2000, Chapter 20, Example Problem 1, printed pp. 20-33–20-34 (validation case).",
    )

    def __init__(self, data_loader: DataLoader | None = None) -> None:
        """Create an analyzer bound to the project HCM registry."""
        self.loader = data_loader or DataLoader()

    def analyze(self, inputs: TwoLaneHighwayInputs) -> CalculationResult:
        """Run two-way operational (LOS) analysis for HCM 2000 Chapter 20.

        Inputs not present in the preliminary UI contract (PHF, separate truck
        and RV percentages, terrain, directional split, BFFS, access density,
        passing-zone share and highway class) are required explicitly here.
        """
        warnings = self._validate_inputs(inputs)
        try:
            table = self.loader.load_table
            access_adjustment = self._access_adjustment(
                table("tabla_20_6_fa"), inputs.access_points_per_km
            )
            fls = self._lane_shoulder_adjustment(
                table("tabla_20_5_fls"), inputs.lane_width_m, inputs.shoulder_width_m
            )
            ffs = inputs.base_free_flow_speed_km_per_h - fls - access_adjustment
            if ffs <= 0:
                raise CalculationInputError("La FFS calculada no es positiva; revise BFFS y geometría.")

            speed = self._flow_path(
                inputs, table("tabla_20_7_fg_velocidad"),
                table("tabla_20_9_equivalentes_velocidad"),
            )
            ptsf_path = self._flow_path(
                inputs, table("tabla_20_8_fg_ptsf"),
                table("tabla_20_10_equivalentes_ptsf"),
            )
            capacities = table("capacidad_dos_carriles_reference")
            two_way_capacity = self._capacity_value(capacities, "combined")
            directional_capacity = self._capacity_value(capacities, "por_direction")
            capacity_check = assess_capacity(
                speed["vp"], ptsf_path["vp"], inputs.major_direction_percent / 100.0,
                two_way_capacity, directional_capacity,
            )

            parameters: dict[str, Any] = {
                "free_flow_speed_adjustment_lane_shoulder_km_per_h": fls,
                "free_flow_speed_adjustment_access_km_per_h": access_adjustment,
                "grade_adjustment_speed": speed["fG"],
                "truck_equivalency_speed": speed["ET"],
                "rv_equivalency_speed": speed["ER"],
                "heavy_vehicle_factor_speed": speed["fHV"],
                "grade_adjustment_ptsf": ptsf_path["fG"],
                "truck_equivalency_ptsf": ptsf_path["ET"],
                "rv_equivalency_ptsf": ptsf_path["ER"],
                "heavy_vehicle_factor_ptsf": ptsf_path["fHV"],
                "capacity_two_way_pc_per_h": two_way_capacity,
                "capacity_per_direction_pc_per_h": directional_capacity,
                "table_records": {
                    "fLS": "Exhibit 20-5; reviewed CSV table_20_5_fls",
                    "fA": "Exhibit 20-6; reviewed CSV table_20_6_fa",
                    "speed_fG": "Exhibit 20-7; reviewed CSV table_20_7_fg_velocidad",
                    "ptsf_fG": "Exhibit 20-8; reviewed CSV table_20_8_fg_ptsf",
                    "speed_equivalencies": "Exhibit 20-9; reviewed CSV table_20_9_equivalentes_velocidad",
                    "ptsf_equivalencies": "Exhibit 20-10; reviewed CSV table_20_10_equivalentes_ptsf",
                    "capacity": "Chapter 20 capacity statement; reviewed capacity CSV",
                },
            }
            intermediate: dict[str, Any] = {
                "free_flow_speed_km_per_h": ffs,
                "speed_flow_bin": speed["flow_range"],
                "speed_vp_pc_per_h": speed["vp"],
                "speed_highest_direction_flow_pc_per_h": capacity_check.highest_directional_flow_speed_pc_per_h,
                "ptsf_flow_bin": ptsf_path["flow_range"],
                "ptsf_vp_pc_per_h": ptsf_path["vp"],
                "ptsf_highest_direction_flow_pc_per_h": capacity_check.highest_directional_flow_ptsf_pc_per_h,
                "volume_capacity_ratio": capacity_check.volume_capacity_ratio,
            }
            if inputs.tpda_veh_per_day is not None:
                demand = calculate_design_hour_volume(
                    inputs.tpda_veh_per_day,
                    float(inputs.k3_design_hour_factor),
                    inputs.major_direction_percent,
                )
                intermediate["design_hour_volume_conversion"] = {
                    "equation": "VHD = TPDA × K3; reparto direccional según Exhibit 20-12",
                    "vhd_two_way_veh_per_h": demand.vhd_two_way_veh_per_h,
                    "major_direction_percent": demand.major_direction_percent,
                    "analysis_direction_share_percent": demand.analysis_direction_share_percent,
                    "vhd_analysis_direction_veh_per_h": demand.vhd_analysis_direction_veh_per_h,
                    "vhd_opposing_direction_veh_per_h": demand.vhd_opposing_direction_veh_per_h,
                    "source_category": "Reparto direccional de HCM 2000, Exhibit 20-12",
                }
            if capacity_check.oversaturated:
                warnings.append(
                    "La demanda excede la capacidad HCM (3,200 pc/h bidireccionales o "
                    "1,700 pc/h en el sentido de mayor flujo); LOS F. HCM advierte que "
                    "ATS y PTSF no son estimaciones confiables en condición sobresaturada."
                )
                return CalculationResult(
                    inputs=asdict(inputs), parameters=parameters,
                    intermediate_results=intermediate,
                    final_results={
                        "capacity_pc_per_h_two_way": two_way_capacity,
                        "volume_capacity_ratio": capacity_check.volume_capacity_ratio,
                        "average_travel_speed_km_per_h": None,
                        "percent_time_spent_following": None,
                        "level_of_service": "F",
                        "other_performance_measures": None,
                    }, warnings=tuple(warnings), formula_references=self.FORMULA_REFERENCES,
                )

            fnp = self._interpolated_table_value(
                table("tabla_20_11_fnp"), "vp_pcph", speed["vp"],
                "no_passing_zones_pct", inputs.no_passing_zones_percent,
                "fnp_reduction_kmh",
            )
            ats = calculate_average_travel_speed(ffs, speed["vp"], fnp)
            fd_np = self._directional_passing_adjustment(
                table("tabla_20_12_fd_np"), ptsf_path["vp"],
                inputs.major_direction_percent, inputs.no_passing_zones_percent,
            )
            if self._uses_printed_nonmonotone_exhibit_value(
                table("tabla_20_12_fd_np"), ptsf_path["vp"],
                inputs.major_direction_percent, inputs.no_passing_zones_percent,
            ):
                warnings.append(
                    "El Exhibit 20-12 impreso presenta valores no monótonos para el "
                    "reparto 70/30 y flujo >=2000 pc/h entre 40% y 60% de zonas de "
                    "no rebase. Se conservó la tabla tal como aparece en el manual."
                )
            bptsf = calculate_base_ptsf(ptsf_path["vp"])
            ptsf = calculate_ptsf(bptsf, fd_np)
            criteria = table("los_carreteras_dos_carriles")
            los = classify_level_of_service(inputs.highway_class, ptsf, ats, criteria)
            other = calculate_other_performance_measures(
                inputs.hourly_volume_veh_per_h, inputs.peak_hour_factor,
                inputs.segment_length_km, ats,
            )
            intermediate.update({
                "fnp_adjustment_km_per_h": fnp,
                "average_travel_speed_km_per_h": ats,
                "base_ptsf_percent": bptsf,
                "fd_np_adjustment_percent": fd_np,
                "percent_time_spent_following": ptsf,
            })
            return CalculationResult(
                inputs=asdict(inputs), parameters=parameters,
                intermediate_results=intermediate,
                final_results={
                    "capacity_pc_per_h_two_way": two_way_capacity,
                    "volume_capacity_ratio": capacity_check.volume_capacity_ratio,
                    "average_travel_speed_km_per_h": ats,
                    "percent_time_spent_following": ptsf,
                    "level_of_service": los,
                    "other_performance_measures": other,
                }, warnings=tuple(warnings), formula_references=self.FORMULA_REFERENCES,
            )
        except DataLoaderError as exc:
            raise CalculationDataError(f"No se pudo recuperar un dato HCM verificado: {exc}") from exc

    @staticmethod
    def _validate_inputs(data: TwoLaneHighwayInputs) -> list[str]:
        """Validate scalar ranges and return method applicability warnings."""
        numeric = asdict(data)
        numeric_fields = (
            "hourly_volume_veh_per_h", "peak_hour_factor", "major_direction_percent",
            "trucks_percent", "recreational_vehicles_percent", "segment_length_km",
            "lane_width_m", "shoulder_width_m", "access_points_per_km",
            "no_passing_zones_percent", "base_free_flow_speed_km_per_h",
        )
        for key in numeric_fields:
            value = numeric[key]
            if value is None:
                raise CalculationInputError(f"El campo obligatorio {key} no fue suministrado.")
            if not isinstance(value, (int, float)) or not isfinite(value):
                raise CalculationInputError(f"{key} debe ser un número finito.")
        demand_values = (
            data.tpda_veh_per_day,
            data.k3_design_hour_factor,
        )
        if all(value is None for value in demand_values):
            pass  # Allows independent legacy calls already supplying an hourly volume.
        elif any(value is None for value in demand_values):
            raise CalculationInputError("Para documentar la conversión a VHD, ingrese TPDA y K3.")
        else:
            demand = calculate_design_hour_volume(
                float(data.tpda_veh_per_day),
                float(data.k3_design_hour_factor),
                float(data.major_direction_percent),
            )
            if abs(demand.vhd_two_way_veh_per_h - data.hourly_volume_veh_per_h) > 1e-6:
                raise CalculationInputError("El volumen horario no coincide con TPDA × K3.")
        for key in ("terrain", "highway_class"):
            if not isinstance(numeric[key], str) or not numeric[key].strip():
                raise CalculationInputError(f"El campo obligatorio {key} no fue suministrado.")
        if data.hourly_volume_veh_per_h <= 0:
            raise CalculationInputError("El volumen horario debe ser mayor que cero.")
        if not 0 < data.peak_hour_factor <= 1:
            raise CalculationInputError("PHF debe estar en el intervalo (0, 1].")
        if data.major_direction_percent not in {50, 60, 70, 80, 90}:
            raise CalculationInputError("La tabla 20-12 solo documenta repartos 50/50 a 90/10 en pasos de 10 puntos.")
        for value, label in ((data.trucks_percent, "Camiones"), (data.recreational_vehicles_percent, "RV"), (data.no_passing_zones_percent, "Zonas de no rebase")):
            if not 0 <= value <= 100:
                raise CalculationInputError(f"{label}: el porcentaje debe estar entre 0 y 100.")
        if data.trucks_percent + data.recreational_vehicles_percent > 100:
            raise CalculationInputError("Camiones y RV no pueden sumar más de 100%.")
        if data.terrain not in {"level", "rolling"}:
            raise CalculationInputError("Este procedimiento de dos sentidos admite terreno level o rolling.")
        if data.highway_class not in {"I", "II"}:
            raise CalculationInputError("La clase de carretera debe ser I o II.")
        if data.segment_length_km < 3.0:
            raise CalculationInputError("El procedimiento de segmento bidireccional se aplica típicamente a tramos de al menos 3.0 km; no se calcula un tramo más corto con esta fase.")
        if data.lane_width_m < 2.7:
            raise CalculationInputError("La tabla 20-5 no contiene anchos de carril menores que 2.7 m.")
        if data.shoulder_width_m < 0:
            raise CalculationInputError("El ancho de berma no puede ser negativo.")
        if data.access_points_per_km < 0:
            raise CalculationInputError("La densidad de accesos no puede ser negativa.")
        if not 70 <= data.base_free_flow_speed_km_per_h <= 110:
            raise CalculationInputError("BFFS debe estar entre 70 y 110 km/h, rango descrito por HCM 2000, capítulo 20.")
        return [
            "BFFS se toma como dato del usuario; HCM 2000 capítulo 20 no proporciona un valor base por defecto.",
            "Las tablas 20-11 y 20-12 se interpolan linealmente entre celdas tabuladas; el procedimiento se contrasta con Example Problem 1.",
        ]

    @staticmethod
    def _flow_path(
        inputs: TwoLaneHighwayInputs, grade_rows: list[dict[str, str]],
        equivalency_rows: list[dict[str, str]],
    ) -> dict[str, float | str]:
        """Select flow-stratified values and apply HCM's iterative bin check."""
        initial_rate = inputs.hourly_volume_veh_per_h / inputs.peak_hour_factor
        terrain_label = TwoLaneHighwayAnalyzer._terrain_label(grade_rows, inputs.terrain)
        equivalency_terrain = TwoLaneHighwayAnalyzer._terrain_label(
            equivalency_rows, inputs.terrain
        )
        grade_record = TwoLaneHighwayAnalyzer._flow_range_record(
            grade_rows, "two_way_flow_pcph_range", initial_rate,
            predicate=lambda r: r["terrain"] == terrain_label,
        )
        eq_record = TwoLaneHighwayAnalyzer._flow_range_record(
            equivalency_rows, "two_way_flow_pcph_range", initial_rate,
            predicate=lambda r: r["vehicle_type"] == "Camiones" and r["terrain"] == equivalency_terrain,
        )
        group = grade_record["two_way_flow_pcph_range"]
        rv_record = next((r for r in equivalency_rows if
            r["two_way_flow_pcph_range"] == group and r["vehicle_type"] == "VR" and r["terrain"] == equivalency_terrain), None)
        if rv_record is None:
            raise CalculationDataError(f"No hay equivalencia VR para el rango {group} y terreno {terrain_label}.")
        fg = float(grade_record["fG"])
        et, er = float(eq_record["equivalent"]), float(rv_record["equivalent"])
        fhv = calculate_heavy_vehicle_factor(
            inputs.trucks_percent, inputs.recreational_vehicles_percent, et, er,
        )
        vp = calculate_equivalent_flow_rate(
            inputs.hourly_volume_veh_per_h, inputs.peak_hour_factor, fg, fhv,
        )
        # HCM Chapter 20 directs moving to the next higher table range if the
        # computed passenger-car flow exceeds the range used for the factors.
        for _ in range(3):
            _, upper = TwoLaneHighwayAnalyzer._range_bounds(group)
            if upper is None or vp <= upper:
                break
            grade_record = TwoLaneHighwayAnalyzer._flow_range_record(
                grade_rows, "two_way_flow_pcph_range", vp,
                predicate=lambda r: r["terrain"] == terrain_label,
            )
            group = grade_record["two_way_flow_pcph_range"]
            eq_record = TwoLaneHighwayAnalyzer._flow_range_record(
                equivalency_rows, "two_way_flow_pcph_range", vp,
                predicate=lambda r: r["vehicle_type"] == "Camiones" and r["terrain"] == equivalency_terrain,
            )
            rv_record = next(r for r in equivalency_rows if
                r["two_way_flow_pcph_range"] == group and r["vehicle_type"] == "VR" and r["terrain"] == equivalency_terrain)
            fg = float(grade_record["fG"])
            et, er = float(eq_record["equivalent"]), float(rv_record["equivalent"])
            fhv = calculate_heavy_vehicle_factor(inputs.trucks_percent, inputs.recreational_vehicles_percent, et, er)
            vp = calculate_equivalent_flow_rate(inputs.hourly_volume_veh_per_h, inputs.peak_hour_factor, fg, fhv)
        else:
            raise CalculationDataError("No se estabilizó la selección iterativa de las tablas de flujo HCM.")
        return {"fG": fg, "ET": et, "ER": er, "fHV": fhv, "vp": vp, "flow_range": group}

    @staticmethod
    def _terrain_label(records: list[dict[str, str]], terrain: str) -> str:
        """Resolve level/rolling to the terminology present in each HCM table."""
        candidates = ("Plano", "Nivel") if terrain == "level" else ("Ondulado",)
        available = {row.get("terrain") for row in records}
        for label in candidates:
            if label in available:
                return label
        raise CalculationDataError(f"No hay filas tabuladas para terreno {terrain!r}.")

    @staticmethod
    def _flow_range_record(
        records: list[dict[str, str]], field: str, flow: float,
        predicate: Callable[[dict[str, str]], bool] = lambda _row: True,
    ) -> dict[str, str]:
        """Select exactly one row whose documented flow interval contains vp."""
        matches=[]
        for row in records:
            if predicate(row) and TwoLaneHighwayAnalyzer._in_flow_range(flow, row[field]):
                matches.append(row)
        if len(matches) != 1:
            raise CalculationDataError(f"Se esperaba un registro único para {field}={flow}; se encontraron {len(matches)}.")
        return matches[0]

    @staticmethod
    def _in_flow_range(flow: float, label: str) -> bool:
        """Test a flow against a table's textual inclusive/exclusive bounds."""
        lower, upper = TwoLaneHighwayAnalyzer._range_bounds(label)
        if label.startswith(">"):
            return flow > (lower or 0) and (upper is None or flow <= upper)
        if label.startswith("<="):
            return flow <= (upper or 0)
        return (lower is None or flow >= lower) and (upper is None or flow <= upper)

    @staticmethod
    def _range_bounds(label: str) -> tuple[float | None, float | None]:
        """Parse numeric endpoints from a verified flow-range label."""
        nums=[float(n) for n in re.findall(r"\d+(?:\.\d+)?", label)]
        if not nums:
            raise CalculationDataError(f"Rango tabulado no reconocible: {label!r}.")
        if label.startswith("<="):
            return None, nums[0]
        if label.startswith(">="):
            return nums[0], None
        if label.startswith(">"):
            return nums[0], nums[1] if len(nums) > 1 else None
        if len(nums) == 2:
            return nums[0], nums[1]
        return nums[0], None

    @staticmethod
    def _lane_shoulder_adjustment(
        records: list[dict[str, str]], lane_width: float, shoulder_width: float,
    ) -> float:
        """Retrieve fLS from Exhibit 20-5 using the source's interval labels."""
        matching=[r for r in records if
            TwoLaneHighwayAnalyzer._matches_interval(lane_width, r["lane_width_m_range"])
            and TwoLaneHighwayAnalyzer._matches_interval(shoulder_width, r["shoulder_width_m_range"])]
        if len(matching) != 1:
            raise CalculationInputError("Ancho de carril/berma fuera de los rangos únicos de Exhibit 20-5.")
        return float(matching[0]["fLS_reduction_kmh"])

    @staticmethod
    def _matches_interval(value: float, label: str) -> bool:
        """Check a numeric geometry value against the table's interval text."""
        tokens=re.findall(r"(>=|<=|>|<)\s*(\d+(?:\.\d+)?)", label)
        if not tokens:
            raise CalculationDataError(f"Intervalo de tabla no reconocido: {label!r}.")
        for operator, raw in tokens:
            bound=float(raw)
            if operator == ">=" and value < bound: return False
            if operator == ">" and value <= bound: return False
            if operator == "<=" and value > bound: return False
            if operator == "<" and value >= bound: return False
        return True

    @staticmethod
    def _access_adjustment(records: list[dict[str, str]], density: float) -> float:
        """Look up fA at a listed Exhibit 20-6 density; no extrapolation."""
        for row in records:
            label=row["access_points_per_km"]
            if label.startswith(">=") and density >= float(label[2:]):
                return float(row["fA_reduction_kmh"])
            if density == float(label):
                return float(row["fA_reduction_kmh"])
        raise CalculationInputError("Exhibit 20-6 no tiene un valor exacto para esta densidad de accesos; use solo 0, 6, 12, 18 o >=24 por km.")

    @staticmethod
    def _capacity_value(records: list[dict[str, str]], capacity_type: str) -> float:
        """Read one specifically identified capacity from the reviewed file."""
        matches=[r for r in records if r["capacity_type"] == capacity_type]
        if len(matches) != 1:
            raise CalculationDataError(f"No existe un registro único de capacidad {capacity_type!r}.")
        return float(matches[0]["capacity"])

    @staticmethod
    def _interpolated_table_value(
        records: list[dict[str, str]], x_field: str, x: float,
        y_field: str, y: float, value_field: str,
    ) -> float:
        """Bilinearly interpolate within Exhibit 20-11 tabulated coordinates."""
        pairs=[]
        for row in records:
            rx, ry = float(row[x_field]), float(row[y_field])
            pairs.append((rx, ry, float(row[value_field])))
        return TwoLaneHighwayAnalyzer._bilinear(pairs, x, y)

    @staticmethod
    def _directional_passing_adjustment(
        records: list[dict[str, str]], flow: float, major_split: float, no_passing: float,
    ) -> float:
        """Interpolate Exhibit 20-12 for its tabulated split and flow domain."""
        split_label=f"{int(major_split)}/{100-int(major_split)}"
        subset=[r for r in records if r["directional_split"] == split_label]
        if not subset:
            raise CalculationDataError(f"Exhibit 20-12 no contiene reparto {split_label}.")
        points=[]
        for row in subset:
            low, high=TwoLaneHighwayAnalyzer._range_bounds(row["vp_pcph"])
            flow_x=high if row["vp_pcph"].startswith("<=") else (low if row["vp_pcph"].startswith(">=") else (low + high) / 2 if low is not None and high is not None else low)
            points.append((float(flow_x), float(row["no_passing_zones_pct"]), float(row["fd_np_increment_ptsf_pct"])))
        return TwoLaneHighwayAnalyzer._bilinear(points, flow, no_passing, clamp_high_ranges=True)

    @staticmethod
    def _uses_printed_nonmonotone_exhibit_value(
        records: list[dict[str, str]], flow: float, major_split: float, no_passing: float,
    ) -> bool:
        """Flag the non-monotone values printed in Exhibit 20-12, without altering them."""
        if major_split != 70 or no_passing <= 40 or no_passing >= 60:
            return False
        rows = [r for r in records if r["directional_split"] == "70/30"]
        # Locate the same flow row at 40% and 60% no-passing zones.
        low_row = next((r for r in rows if r["vp_pcph"] == ">=2000" and r["no_passing_zones_pct"] == "40"), None)
        high_row = next((r for r in rows if r["vp_pcph"] == ">=2000" and r["no_passing_zones_pct"] == "60"), None)
        if low_row is None or high_row is None:
            return False
        lower, upper = float(low_row["fd_np_increment_ptsf_pct"]), float(high_row["fd_np_increment_ptsf_pct"])
        return flow >= 2000 and lower > upper

    @staticmethod
    def _bilinear(
        points: list[tuple[float, float, float]], x: float, y: float,
        *, clamp_high_ranges: bool = False,
    ) -> float:
        """Linear interpolation in both axes over a documented rectangular grid."""
        xs=sorted({p[0] for p in points}); ys=sorted({p[1] for p in points})
        if y < ys[0] or y > ys[-1]:
            raise CalculationInputError(f"El valor transversal {y} queda fuera del rango tabulado {ys[0]}–{ys[-1]}.")
        if x < xs[0] or x > xs[-1]:
            if not clamp_high_ranges or x < xs[0]:
                raise CalculationInputError(f"El flujo {x} queda fuera del rango tabulado {xs[0]}–{xs[-1]}.")
            x=xs[-1]
        x0,x1=TwoLaneHighwayAnalyzer._bracket(xs,x)
        y0,y1=TwoLaneHighwayAnalyzer._bracket(ys,y)
        grid={(px,py):val for px,py,val in points}
        try:
            a=TwoLaneHighwayAnalyzer._linear(x,x0,x1,grid[(x0,y0)],grid[(x1,y0)])
            b=TwoLaneHighwayAnalyzer._linear(x,x0,x1,grid[(x0,y1)],grid[(x1,y1)])
        except KeyError as exc:
            raise CalculationDataError("La tabla HCM no forma una malla completa para interpolar.") from exc
        return TwoLaneHighwayAnalyzer._linear(y,y0,y1,a,b)

    @staticmethod
    def _bracket(values: list[float], value: float) -> tuple[float,float]:
        """Return the two tabulated coordinates surrounding a value."""
        if value in values: return value,value
        for low,high in zip(values,values[1:]):
            if low < value < high: return low,high
        raise CalculationInputError(f"No se puede interpolar el valor {value} en la tabla.")

    @staticmethod
    def _linear(value: float, low: float, high: float, low_result: float, high_result: float) -> float:
        """Interpolate between two table coordinates without extrapolation."""
        if low == high: return low_result
        return low_result + (value-low)/(high-low)*(high_result-low_result)


def analyze_two_way_segment(inputs: TwoLaneHighwayInputs) -> CalculationResult:
    """Convenience function for standalone use without an interface layer."""
    return TwoLaneHighwayAnalyzer().analyze(inputs)
