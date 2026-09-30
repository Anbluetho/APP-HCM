"""Orchestration for HCM 2000 specific-upgrade and specific-downgrade analysis."""

from __future__ import annotations

from dataclasses import asdict, replace
from math import isfinite
from typing import Any

from calculations.exceptions import CalculationDataError, CalculationInputError
from calculations.design_hour_volume import calculate_design_hour_volume
from calculations.specific_grade.flow import (
    DirectionalFlowResult,
    calculate_directional_flow,
)
from calculations.specific_grade.performance import (
    calculate_directional_ats,
    calculate_directional_base_ptsf,
    calculate_directional_ptsf,
    interpolate_directional_no_passing_adjustment,
    lookup_ptsf_coefficients,
)
from calculations.two_lane_highway import TwoLaneHighwayAnalyzer
from data.data_loader import DataLoader, DataLoaderError
from models.calculation_result import CalculationResult
from models.specific_grade import SpecificGradeInputs
from calculations.los import classify_level_of_service


SPECIFIC_GRADE_TABLES = {
    "exhibit_20_13": "specific_grade_20_13_ats_fg",
    "exhibit_20_14": "specific_grade_20_14_ptsf_fg",
    "exhibit_20_15": "specific_grade_20_15_ats_et",
    "exhibit_20_16": "specific_grade_20_16_ptsf_et_er",
    "exhibit_20_17": "specific_grade_20_17_ats_er",
    "exhibit_20_18": "specific_grade_20_18_crawl_etc",
    "exhibit_20_19": "specific_grade_20_19_ats_fnp",
    "exhibit_20_20": "specific_grade_20_20_ptsf_fnp",
    "exhibit_20_21": "specific_grade_20_21_ptsf_coefficients",
    "specific_downgrade_fG": "specific_downgrade_fg_reference",
    "tabla_20_5_fls": "tabla_20_5_fls",
    "tabla_20_6_fa": "tabla_20_6_fa",
    "tabla_20_9_equivalentes_velocidad": "tabla_20_9_equivalentes_velocidad",
    "tabla_20_10_equivalentes_ptsf": "tabla_20_10_equivalentes_ptsf",
    "los_carreteras_dos_carriles": "los_carreteras_dos_carriles",
    "capacidad_dos_carriles_reference": "capacidad_dos_carriles_reference",
}

SPECIFIC_GRADE_TABLE_LABELS = (
    ("specific_grade_20_13_ats_fg", "fG de ATS en ascenso específico (Exhibit 20-13)"),
    ("specific_grade_20_14_ptsf_fg", "fG de PTSF en ascenso específico (Exhibit 20-14)"),
    ("specific_grade_20_15_ats_et", "ET de ATS en ascenso específico (Exhibit 20-15)"),
    ("specific_grade_20_16_ptsf_et_er", "ET/ER de PTSF en ascenso específico (Exhibit 20-16)"),
    ("specific_grade_20_17_ats_er", "ER de ATS en ascenso específico (Exhibit 20-17)"),
    ("specific_grade_20_18_crawl_etc", "ETC para velocidad de arrastre (Exhibit 20-18)"),
    ("specific_grade_20_19_ats_fnp", "Ajuste ATS direccional (Exhibit 20-19)"),
    ("specific_grade_20_20_ptsf_fnp", "Ajuste PTSF direccional (Exhibit 20-20)"),
    ("specific_grade_20_21_ptsf_coefficients", "Coeficientes PTSF (Exhibit 20-21)"),
    ("specific_downgrade_fg_reference", "Referencia fG para descenso específico"),
    ("tabla_20_5_fls", "Ajuste geométrico FFS (Exhibit 20-5)"),
    ("tabla_20_6_fa", "Ajuste por accesos (Exhibit 20-6)"),
    ("tabla_20_9_equivalentes_velocidad", "Equivalencias ATS en terreno nivel (Exhibit 20-9)"),
    ("tabla_20_10_equivalentes_ptsf", "Equivalencias PTSF en terreno nivel (Exhibit 20-10)"),
    ("los_carreteras_dos_carriles", "Criterios LOS de dos carriles"),
    ("capacidad_dos_carriles_reference", "Capacidad direccional de dos carriles"),
)


def verify_specific_grade_tables(
    data_loader: DataLoader | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Verify the source tables needed by the specific-grade procedure."""
    loader = data_loader or DataLoader()
    results: list[dict[str, Any]] = []
    all_verified = True
    for table_id, label in SPECIFIC_GRADE_TABLE_LABELS:
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


class SpecificGradeAnalyzer:
    """Calculate ATS, PTSF, capacity, and LOS for one directional grade segment."""

    FORMULA_REFERENCES = (
        "HCM 2000, Chapter 20, Equations 20-2, 20-4, and 20-12 through 20-17.",
        "HCM 2000, Chapter 20, Exhibits 20-5, 20-6, 20-9, and 20-10.",
        "HCM 2000, Chapter 20, Exhibits 20-13 through 20-21; Exhibit 20-18 and Equation 20-14 when crawl-speed trucks apply.",
        "HCM 2000, Chapter 20, directional capacity of 1,700 pc/h; LOS criteria in Exhibits 20-2 through 20-4.",
    )

    def __init__(self, data_loader: DataLoader | None = None) -> None:
        self.loader = data_loader or DataLoader()

    def analyze(self, inputs: SpecificGradeInputs) -> CalculationResult:
        """Run a source-backed, independent specific-grade analysis."""
        inputs = self._with_design_hour_volumes(inputs)
        self.validate_inputs(inputs)
        try:
            tables = {
                key: self.loader.load_table(table_id)
                for key, table_id in SPECIFIC_GRADE_TABLES.items()
            }
            f_ls = TwoLaneHighwayAnalyzer._lane_shoulder_adjustment(
                tables["tabla_20_5_fls"], inputs.lane_width_m, inputs.shoulder_width_m
            )
            f_a = TwoLaneHighwayAnalyzer._access_adjustment(
                tables["tabla_20_6_fa"], inputs.access_points_per_km
            )
            ffs_analysis = inputs.base_free_flow_speed_analysis_km_per_h - f_ls - f_a
            if ffs_analysis <= 0:
                raise CalculationInputError("La FFS del sentido analizado no es positiva.")

            analysis_grade = inputs.analysis_grade_direction
            opposing_grade = "downgrade" if analysis_grade == "upgrade" else "upgrade"
            downhill_role = "analysis" if analysis_grade == "downgrade" else "opposing"
            ffs_downhill = ffs_analysis if downhill_role == "analysis" else None
            if inputs.downhill_crawl_condition and downhill_role == "opposing":
                base_opposing = inputs.base_free_flow_speed_opposing_km_per_h
                if base_opposing is None:
                    raise CalculationInputError(
                        "Falta la BFFS del sentido descendente opuesto para aplicar el Exhibit 20-18."
                    )
                ffs_downhill = base_opposing - f_ls - f_a
                if ffs_downhill <= 0:
                    raise CalculationInputError("La FFS del sentido descendente no es positiva.")

            direction_inputs = {
                "analysis": {
                    "volume": inputs.analysis_volume_veh_per_h,
                    "grade": analysis_grade,
                    "trucks": inputs.analysis_trucks_percent,
                    "rvs": inputs.analysis_rvs_percent,
                },
                "opposing": {
                    "volume": inputs.opposing_volume_veh_per_h,
                    "grade": opposing_grade,
                    "trucks": inputs.opposing_trucks_percent,
                    "rvs": inputs.opposing_rvs_percent,
                },
            }
            flow_results: dict[str, DirectionalFlowResult] = {}
            for purpose in ("ats", "ptsf"):
                for role, values in direction_inputs.items():
                    is_downhill = values["grade"] == "downgrade"
                    use_crawl = bool(inputs.downhill_crawl_condition and is_downhill and purpose == "ats")
                    flow_results[f"{purpose}_{role}"] = calculate_directional_flow(
                        volume_veh_per_h=float(values["volume"]),
                        peak_hour_factor=inputs.peak_hour_factor,
                        grade_direction=str(values["grade"]),
                        grade_percent=inputs.grade_percent,
                        grade_length_km=inputs.grade_length_km,
                        purpose=purpose,
                        trucks_percent=float(values["trucks"]),
                        rvs_percent=float(values["rvs"]),
                        tables=tables,
                        use_crawl_equation=use_crawl,
                        trucks_at_crawl_percent=(
                            inputs.downhill_trucks_at_crawl_percent if use_crawl else None
                        ),
                        truck_crawl_speed_km_per_h=(
                            inputs.downhill_truck_crawl_speed_km_per_h if use_crawl else None
                        ),
                        free_flow_speed_km_per_h=(ffs_downhill if use_crawl else None),
                    )

            cap_records = tables["capacidad_dos_carriles_reference"]
            directional_capacity = TwoLaneHighwayAnalyzer._capacity_value(cap_records, "por_direction")
            at_capacity = any(
                flow.flow_pc_per_h >= directional_capacity
                for flow in flow_results.values()
            )
            v_c = flow_results["ats_analysis"].flow_pc_per_h / directional_capacity

            parameters = self._parameter_results(
                flow_results, f_ls, f_a, directional_capacity,
                inputs, ffs_analysis,
            )
            intermediate: dict[str, Any] = {
                "free_flow_speed_analysis_km_per_h": ffs_analysis,
                "flow_iterations": {
                    name: [asdict(step) for step in result.iterations]
                    for name, result in flow_results.items()
                },
                "capacity_analysis_vd_ats_pc_per_h": flow_results["ats_analysis"].flow_pc_per_h,
                "capacity_analysis_vd_ptsf_pc_per_h": flow_results["ptsf_analysis"].flow_pc_per_h,
                "capacity_opposing_vo_ats_pc_per_h": flow_results["ats_opposing"].flow_pc_per_h,
                "capacity_opposing_vo_ptsf_pc_per_h": flow_results["ptsf_opposing"].flow_pc_per_h,
                "volume_capacity_ratio": v_c,
            }
            if inputs.tpda_veh_per_day is not None:
                intermediate["design_hour_volume_conversion"] = {
                    "equation": (
                        "VHD = TPDA × K3; reparto según Exhibit 20-12; "
                        "la dirección analizada utiliza la fracción mayor o menor elegida"
                    ),
                    "vhd_two_way_veh_per_h": inputs.tpda_veh_per_day * inputs.k3_design_hour_factor,
                    "major_direction_percent": inputs.major_direction_percent,
                    "analysis_direction_share_percent": (
                        inputs.major_direction_percent
                        if inputs.analysis_direction_is_major
                        else 100 - inputs.major_direction_percent
                    ),
                    "vhd_analysis_direction_veh_per_h": inputs.analysis_volume_veh_per_h,
                    "vhd_opposing_direction_veh_per_h": inputs.opposing_volume_veh_per_h,
                    "source_category": "Categoría direccional HCM 2000, Exhibit 20-12",
                }
            if at_capacity:
                return CalculationResult(
                    inputs=asdict(inputs), parameters=parameters,
                    intermediate_results=intermediate,
                    final_results={
                        "average_travel_speed_km_per_h": None,
                        "percent_time_spent_following": None,
                        "analysis_flow_ats_pc_per_h": flow_results["ats_analysis"].flow_pc_per_h,
                        "opposing_flow_ats_pc_per_h": flow_results["ats_opposing"].flow_pc_per_h,
                        "analysis_flow_ptsf_pc_per_h": flow_results["ptsf_analysis"].flow_pc_per_h,
                        "opposing_flow_ptsf_pc_per_h": flow_results["ptsf_opposing"].flow_pc_per_h,
                        "capacity_pc_per_h_direction": directional_capacity,
                        "volume_capacity_ratio": v_c,
                        "level_of_service": "F",
                        "other_performance_measures": None,
                    },
                    warnings=(
                        "Uno o más flujos direccionales equivalentes (vd o vo) alcanzan o exceden "
                        "1.700 pc/h; el worksheet HCM indica terminar el análisis con LOS F. "
                        "ATS y PTSF no se estiman en esta condición.",
                    ),
                    formula_references=self.FORMULA_REFERENCES,
                )

            fnp_ats = interpolate_directional_no_passing_adjustment(
                tables["exhibit_20_19"],
                free_flow_speed_km_per_h=ffs_analysis,
                opposing_flow_pc_per_h=flow_results["ats_opposing"].flow_pc_per_h,
                no_passing_zones_percent=inputs.no_passing_zones_percent,
                value_field="fnp_kmh",
            )
            ats = calculate_directional_ats(
                ffs_analysis,
                flow_results["ats_analysis"].flow_pc_per_h,
                flow_results["ats_opposing"].flow_pc_per_h,
                fnp_ats,
            )
            a, b = lookup_ptsf_coefficients(
                tables["exhibit_20_21"], flow_results["ptsf_opposing"].flow_pc_per_h
            )
            bptsf = calculate_directional_base_ptsf(
                flow_results["ptsf_analysis"].flow_pc_per_h, a, b
            )
            fnp_ptsf = interpolate_directional_no_passing_adjustment(
                tables["exhibit_20_20"],
                free_flow_speed_km_per_h=ffs_analysis,
                opposing_flow_pc_per_h=flow_results["ptsf_opposing"].flow_pc_per_h,
                no_passing_zones_percent=inputs.no_passing_zones_percent,
                value_field="fnp_ptsf_pct",
            )
            ptsf = calculate_directional_ptsf(bptsf, fnp_ptsf)
            los = classify_level_of_service(
                inputs.highway_class, ptsf, ats, tables["los_carreteras_dos_carriles"]
            )
            intermediate.update({
                "adjustment_no_passing_ats_km_per_h": fnp_ats,
                "base_ptsf_percent": bptsf,
                "adjustment_no_passing_ptsf_percent": fnp_ptsf,
                "ptsf_coefficients_a": a,
                "ptsf_coefficients_b": b,
            })
            return CalculationResult(
                inputs=asdict(inputs), parameters=parameters,
                intermediate_results=intermediate,
                final_results={
                    "average_travel_speed_km_per_h": ats,
                    "percent_time_spent_following": ptsf,
                    "analysis_flow_ats_pc_per_h": flow_results["ats_analysis"].flow_pc_per_h,
                    "opposing_flow_ats_pc_per_h": flow_results["ats_opposing"].flow_pc_per_h,
                    "analysis_flow_ptsf_pc_per_h": flow_results["ptsf_analysis"].flow_pc_per_h,
                    "opposing_flow_ptsf_pc_per_h": flow_results["ptsf_opposing"].flow_pc_per_h,
                    "capacity_pc_per_h_direction": directional_capacity,
                    "volume_capacity_ratio": v_c,
                    "level_of_service": los,
                    "other_performance_measures": None,
                },
                warnings=(), formula_references=self.FORMULA_REFERENCES,
            )
        except DataLoaderError as exc:
            raise CalculationDataError(
                f"No se pudo recuperar un dato HCM verificado para pendiente específica: {exc}"
            ) from exc

    @staticmethod
    def validate_inputs(inputs: SpecificGradeInputs) -> None:
        """Validate inputs and HCM-specific grade applicability conditions."""
        inputs = SpecificGradeAnalyzer._with_design_hour_volumes(inputs)
        if inputs.analysis_grade_direction not in {"upgrade", "downgrade"}:
            raise CalculationInputError("Seleccione ascenso o descenso para la dirección analizada.")
        numeric = {
            "pendiente": inputs.grade_percent,
            "longitud de pendiente": inputs.grade_length_km,
            "volumen analizado": inputs.analysis_volume_veh_per_h,
            "volumen opuesto": inputs.opposing_volume_veh_per_h,
            "PHF": inputs.peak_hour_factor,
            "camiones sentido analizado": inputs.analysis_trucks_percent,
            "RV sentido analizado": inputs.analysis_rvs_percent,
            "camiones sentido opuesto": inputs.opposing_trucks_percent,
            "RV sentido opuesto": inputs.opposing_rvs_percent,
            "ancho de carril": inputs.lane_width_m,
            "ancho de berma": inputs.shoulder_width_m,
            "puntos de acceso": inputs.access_points_per_km,
            "zonas de no rebase": inputs.no_passing_zones_percent,
            "BFFS sentido analizado": inputs.base_free_flow_speed_analysis_km_per_h,
        }
        for name, value in numeric.items():
            if not isinstance(value, (int, float)) or not isfinite(value):
                raise CalculationInputError(f"El campo {name} debe ser un número finito.")
        if inputs.grade_percent < 3.0:
            raise CalculationInputError(
                "El procedimiento de pendiente específica requiere una pendiente de al menos 3 %. "
                "Para pendientes menores, seleccione el procedimiento general si su tramo cumple sus condiciones."
            )
        minimum_length = 0.4 if inputs.analysis_grade_direction == "upgrade" else 1.0
        if inputs.grade_length_km < minimum_length:
            condition = (
                "Un ascenso de al menos 3 % puede analizarse específicamente desde 0,4 km; "
                "desde 1,0 km el HCM exige ese análisis."
                if inputs.analysis_grade_direction == "upgrade"
                else "Un descenso de al menos 3 % debe analizarse específicamente desde 1,0 km."
            )
            raise CalculationInputError(condition)
        if inputs.analysis_volume_veh_per_h <= 0 or inputs.opposing_volume_veh_per_h < 0:
            raise CalculationInputError("El volumen analizado debe ser mayor que cero y el volumen opuesto no puede ser negativo.")
        if not 0 < inputs.peak_hour_factor <= 1:
            raise CalculationInputError("PHF debe estar en el intervalo (0, 1].")
        for name, value in (
            ("Camiones sentido analizado", inputs.analysis_trucks_percent),
            ("RV sentido analizado", inputs.analysis_rvs_percent),
            ("Camiones sentido opuesto", inputs.opposing_trucks_percent),
            ("RV sentido opuesto", inputs.opposing_rvs_percent),
            ("Zonas de no rebase", inputs.no_passing_zones_percent),
        ):
            if not 0 <= value <= 100:
                raise CalculationInputError(f"{name} debe estar entre 0 y 100 %.")
        if inputs.analysis_trucks_percent + inputs.analysis_rvs_percent > 100:
            raise CalculationInputError("Camiones y RV exceden 100 % en el sentido analizado.")
        if inputs.opposing_trucks_percent + inputs.opposing_rvs_percent > 100:
            raise CalculationInputError("Camiones y RV exceden 100 % en el sentido opuesto.")
        if inputs.highway_class not in {"I", "II"}:
            raise CalculationInputError("El LOS de dos carriles está disponible aquí para clases HCM I y II.")
        if inputs.lane_width_m < 2.7 or inputs.shoulder_width_m < 0:
            raise CalculationInputError("Ancho de carril o berma fuera del dominio de Exhibit 20-5.")
        if inputs.access_points_per_km < 0:
            raise CalculationInputError("La densidad de accesos no puede ser negativa.")
        if inputs.access_points_per_km not in {0, 6, 12, 18} and inputs.access_points_per_km < 24:
            raise CalculationInputError("Exhibit 20-6 contiene categorías 0, 6, 12, 18 y >=24 accesos/km.")
        if not 70 <= inputs.base_free_flow_speed_analysis_km_per_h <= 110:
            raise CalculationInputError("La BFFS analizada debe estar entre 70 y 110 km/h.")
        if inputs.downhill_crawl_condition is None:
            raise CalculationInputError(
                "Indique si hay camiones a velocidad de arrastre en el sentido descendente."
            )
        if inputs.downhill_crawl_condition:
            if inputs.downhill_trucks_at_crawl_percent is None:
                raise CalculationInputError(
                    "Falta la proporción de camiones que usa velocidad de arrastre en el descenso."
                )
            if inputs.downhill_truck_crawl_speed_km_per_h is None:
                raise CalculationInputError("Falta la velocidad de arrastre de los camiones en el descenso.")
            if inputs.analysis_grade_direction == "upgrade" and inputs.base_free_flow_speed_opposing_km_per_h is None:
                raise CalculationInputError(
                    "Falta la BFFS del sentido descendente opuesto para aplicar el Exhibit 20-18."
                )
            if inputs.base_free_flow_speed_opposing_km_per_h is not None and not 70 <= inputs.base_free_flow_speed_opposing_km_per_h <= 110:
                raise CalculationInputError("La BFFS opuesta debe estar entre 70 y 110 km/h.")
            if not 0 < inputs.downhill_trucks_at_crawl_percent <= 100:
                raise CalculationInputError("La proporción de camiones a velocidad de arrastre debe estar en (0, 100] %.")
            if inputs.downhill_truck_crawl_speed_km_per_h <= 0:
                raise CalculationInputError("La velocidad de arrastre debe ser mayor que cero.")

    @staticmethod
    def _with_design_hour_volumes(inputs: SpecificGradeInputs) -> SpecificGradeInputs:
        """Derive hourly volumes using the selected Exhibit 20-12 category."""
        demand_values = (
            inputs.tpda_veh_per_day,
            inputs.k3_design_hour_factor,
            inputs.major_direction_percent,
        )
        if all(value is None for value in demand_values):
            return inputs  # Compatibility for direct engine callers with observed Vd/Vo.
        if any(value is None for value in demand_values):
            raise CalculationInputError("Para derivar los volúmenes por sentido, ingrese TPDA, K3 y la categoría direccional HCM (Exhibit 20-12).")
        if inputs.analysis_direction_is_major is None:
            raise CalculationInputError("Indique si la pendiente analizada corresponde al sentido de mayor o menor flujo.")
        demand = calculate_design_hour_volume(
            float(inputs.tpda_veh_per_day),
            float(inputs.k3_design_hour_factor),
            float(inputs.major_direction_percent),
            analysis_direction_is_major=inputs.analysis_direction_is_major,
        )
        return replace(
            inputs,
            analysis_volume_veh_per_h=demand.vhd_analysis_direction_veh_per_h,
            opposing_volume_veh_per_h=demand.vhd_opposing_direction_veh_per_h,
        )

    @staticmethod
    def _parameter_results(
        flows: dict[str, DirectionalFlowResult], f_ls: float, f_a: float,
        capacity: float, inputs: SpecificGradeInputs,
        ffs_analysis: float,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "free_flow_speed_adjustment_lane_shoulder_km_per_h": f_ls,
            "free_flow_speed_adjustment_access_km_per_h": f_a,
            "free_flow_speed_analysis_km_per_h": ffs_analysis,
            "capacity_per_direction_pc_per_h": capacity,
            "grade_direction_analysis": inputs.analysis_grade_direction,
            "grade_direction_opposing": "downgrade" if inputs.analysis_grade_direction == "upgrade" else "upgrade",
            "grade_percent": inputs.grade_percent,
            "grade_length_km": inputs.grade_length_km,
            "table_records": {
                "ATS_upgrade": "HCM 2000 Chapter 20, Exhibits 20-13, 20-15, 20-17",
                "PTSF_upgrade": "HCM 2000 Chapter 20, Exhibits 20-14, 20-16",
                "directional_no_passing_ATS": "HCM 2000 Chapter 20, Exhibit 20-19",
                "directional_no_passing_PTSF": "HCM 2000 Chapter 20, Exhibit 20-20",
                "directional_PTSF_coefficients": "HCM 2000 Chapter 20, Exhibit 20-21",
            },
        }
        for name, flow in flows.items():
            result[f"grade_factor_{name}"] = flow.grade_factor
            result[f"truck_equivalency_{name}"] = flow.truck_equivalency
            result[f"rv_equivalency_{name}"] = flow.rv_equivalency
            result[f"heavy_vehicle_factor_{name}"] = flow.heavy_vehicle_factor
            if flow.crawl_truck_equivalency is not None:
                result[f"crawl_truck_equivalency_{name}"] = flow.crawl_truck_equivalency
        if inputs.downhill_crawl_condition:
            result["crawl_equation_source"] = "HCM Chapter 20 Equation 20-14 / Exhibit 20-18"
        return result


def analyze_specific_grade(inputs: SpecificGradeInputs) -> CalculationResult:
    """Convenience entry point for standalone specific-grade analysis."""
    return SpecificGradeAnalyzer().analyze(inputs)
