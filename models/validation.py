"""Validate the complete input contract for the selected HCM procedure."""

from typing import Any

from models.input_data import AnalysisInput
from calculations.design_hour_volume import calculate_design_hour_volume
from calculations.exceptions import CalculationInputError


def validate_analysis_input(data: AnalysisInput) -> list[str]:
    """Return clear errors before adapting inputs to the HCM engine."""
    errors: list[str] = []
    project = data["project"]
    if not project["project_name"].strip():
        errors.append("Ingrese el nombre del proyecto.")
    if not project["location"].strip():
        errors.append("Ingrese la ubicación del tramo analizado.")

    facility = data["facility"]["facility_type"]
    multilane = facility == "Carretera multicarril"
    geometry = data["geometry"]
    if multilane:
        if geometry["lane_width_m"] is None or geometry["lane_width_m"] < 3.0:
            errors.append("El ancho de carril multicarril debe ser al menos 3,0 m según la tabla del documento de referencia.")
        if geometry["lanes_per_direction"] not in {2, 3}:
            errors.append("Seleccione 2 o 3 carriles por sentido, rango documentado para el ajuste de despeje lateral.")
        if geometry["lateral_clearance_m"] is None or not 0 <= geometry["lateral_clearance_m"] <= 3.6:
            errors.append("Ingrese el despeje lateral total entre 0 y 3,6 m.")
        if geometry["median_type"] not in {"divided", "undivided"}:
            errors.append("Seleccione el tipo de mediana para el procedimiento multicarril.")
    else:
        _require_positive(errors, geometry["segment_length_km"], "La longitud del tramo")
        if geometry["segment_length_km"] is not None and geometry["segment_length_km"] < 3:
            errors.append("Este procedimiento HCM de segmento bidireccional requiere típicamente una longitud de al menos 3.0 km.")
        if geometry["lane_width_m"] is None or geometry["lane_width_m"] < 2.7:
            errors.append("El ancho de carril debe ser al menos 2.7 m para encontrar una categoría en Exhibit 20-5.")
        _require_nonnegative(errors, geometry["shoulder_width_m"], "El ancho de berma")
        if geometry["shoulder_width_m"] is None:
            errors.append("Ingrese el ancho de berma requerido por Exhibit 20-5.")

    traffic = data["traffic"]
    _require_positive(errors, traffic["tpda_veh_per_day"], "El TPDA")
    k3 = traffic["k3_design_hour_factor"]
    if k3 is None or not 0 < k3 <= 1:
        errors.append("K3 debe ser una fracción mayor que 0 y menor o igual que 1.")
    phf = traffic["peak_hour_factor"]
    if phf is None or not 0 < phf <= 1:
        errors.append("Ingrese PHF mayor que cero y menor o igual que 1.")
    hcm_major_split = traffic["major_direction_percent"]
    if hcm_major_split not in {50, 60, 70, 80, 90}:
        errors.append("Seleccione una categoría direccional tabulada en Exhibit 20-12 (50/50 a 90/10).")
    elif traffic["tpda_veh_per_day"] is not None and k3 is not None and 0 < k3 <= 1:
        try:
            calculate_design_hour_volume(
                float(traffic["tpda_veh_per_day"]), float(k3), float(hcm_major_split)
            )
        except (CalculationInputError, TypeError, ValueError) as exc:
            if str(exc) not in errors:
                errors.append(str(exc))
    trucks = traffic["trucks_percent"]
    rvs = traffic["recreational_vehicles_percent"]
    _require_percentage(errors, trucks, "El porcentaje de camiones y buses")
    _require_percentage(errors, rvs, "El porcentaje de vehículos recreacionales")
    if trucks is not None and rvs is not None and trucks + rvs > 100:
        errors.append("Los porcentajes de camiones/buses y vehículos recreacionales no pueden sumar más de 100%.")

    operation = data["operation"]
    allowed_terrain = {"plano", "ondulado", "montanoso", "escarpado"} if multilane else {"plano", "ondulado"}
    if operation["terrain"] is None:
        errors.append("Seleccione el tipo de terreno.")
    elif operation["terrain"] not in allowed_terrain:
        errors.append("Para dos carriles, el procedimiento general integrado solo contiene tablas para terreno plano/nivel y ondulado. Los terrenos con pendientes específicas requieren tablas adicionales.")
    if not multilane and operation["highway_class"] not in {"I", "II", "III"}:
        errors.append("Seleccione la clase HCM I o II para determinar LOS en dos carriles.")
    elif not multilane and operation["highway_class"] == "III":
        errors.append("La Clase III está definida en el material de referencia, pero no se puede calcular todavía: falta incorporar y verificar su criterio PFFS del HCM 2000.")

    additional = data["procedure_additional"]
    access_density = additional["access_points_per_km"]
    if access_density is None or access_density < 0:
        errors.append("Ingrese una densidad de puntos de acceso no negativa.")
    elif access_density not in {0, 6, 12, 18} and access_density < 24:
        errors.append("Exhibit 20-6 contiene categorías 0, 6, 12, 18 y ≥24 accesos/km; no interpole una categoría no documentada.")
    if multilane:
        if additional["driver_population_factor"] not in {0.85, 0.9, 0.95, 1.0}:
            errors.append("Seleccione fP documentado (0,85; 0,90; 0,95 o 1,00) para el análisis multicarril.")
        if operation["terrain"] == "escarpado":
            errors.append("El documento adjunto no incluye factores de equivalencia para terreno escarpado; falta esa tabla para calcular.")
    else:
        _require_percentage(
            errors, additional["no_passing_zones_percent"],
            "El porcentaje de zonas de no rebase",
        )
    bffs = additional["base_free_flow_speed_km_per_h"]
    if bffs is None or not 70 <= bffs <= 110:
        errors.append("Ingrese BFFS entre 70 y 110 km/h según el rango descrito en el capítulo 20.")
    return errors


def _require_positive(errors: list[str], value: Any, label: str) -> None:
    """Add an error unless an optional numeric value is greater than zero."""
    if value is None or value <= 0:
        errors.append(f"{label} debe ser mayor que cero.")


def _require_nonnegative(errors: list[str], value: Any, label: str) -> None:
    """Add an error when a supplied optional numeric value is negative."""
    if value is not None and value < 0:
        errors.append(f"{label} no puede ser negativo.")


def _require_percentage(errors: list[str], value: Any, label: str) -> None:
    """Require a numeric percentage within the inclusive 0–100 bounds."""
    if value is None or not 0 <= value <= 100:
        errors.append(f"{label} debe estar entre 0 y 100%.")
