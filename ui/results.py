"""Neutral, auditable Streamlit presentation for HCM analysis reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from models.calculation_result import CalculationResult
from reports.csv_export import report_to_csv
from reports.report_data import (
    APPLICATION_VERSION,
    PROCEDURE_NAME,
    build_report_payload,
)


def render_results(
    result: CalculationResult | None,
    submitted_inputs: dict[str, Any] | None = None,
    messages: list[str] | tuple[str, ...] = (),
) -> None:
    """Render the nine report sections and offer a CSV download."""
    st.header("Resultados del cálculo")
    if result is None:
        st.info("No hay resultados calculados para mostrar.")
        if messages:
            _render_warnings(messages, None)
        return

    submitted_inputs = submitted_inputs or {}
    payload = build_report_payload(submitted_inputs, result)
    metadata = payload["metadata"]
    final = result.final_results
    intermediate = result.intermediate_results
    parameters = result.parameters

    st.subheader("1. RESUMEN")
    with st.container(border=True):
        st.write(f"**Proyecto:** {metadata['project'] or 'Sin nombre'}")
        st.write(f"**Ubicación:** {metadata['location'] or 'Sin especificar'}")
        st.write(f"**Fecha del informe:** {metadata['date']}")
        st.write(f"**Procedimiento:** {metadata['procedure']}")
        st.caption(f"Versión del aplicativo: {APPLICATION_VERSION}")
        st.metric("NIVEL DE SERVICIO (LOS)", str(final.get("level_of_service", "No calculado")))
    st.download_button(
        "Descargar resultados en CSV",
        data=report_to_csv(payload),
        file_name=f"informe_hcm_{_safe_filename(metadata['project'])}.csv",
        mime="text/csv; charset=utf-8",
        key="download_hcm_report_csv",
    )

    st.subheader("2. DATOS DE ENTRADA")
    st.dataframe(_input_rows(result, submitted_inputs), hide_index=True, width="stretch")

    st.subheader("3. FACTORES HCM")
    st.dataframe(_factor_rows(parameters, intermediate), hide_index=True, width="stretch")

    st.subheader("4. CÁLCULOS INTERMEDIOS")
    st.dataframe(_intermediate_rows(intermediate), hide_index=True, width="stretch")
    with st.expander("Ecuaciones y criterios aplicados"):
        st.dataframe(_procedure_rows(result), hide_index=True, width="stretch")

    st.subheader("5. CAPACIDAD")
    cols = st.columns(3)
    is_multilane = "lanes_per_direction" in result.inputs
    capacity_title = "Capacidad por sentido" if is_multilane else "Capacidad bidireccional"
    capacity_value = final.get("capacity_pc_per_h_direction") if is_multilane else final.get("capacity_pc_per_h_two_way")
    cols[0].metric(capacity_title, _format(capacity_value, 0, "pc/h"))
    cols[1].metric(
        "Capacidad por carril" if is_multilane else "Capacidad por sentido",
        _format(final.get("capacity_pc_per_h_per_lane") if is_multilane else parameters.get("capacity_per_direction_pc_per_h"), 0, "pc/h"),
    )
    cols[2].metric("Relación volumen/capacidad", _format(final.get("volume_capacity_ratio"), 3))

    st.subheader("6. MEDIDAS DE DESEMPEÑO")
    cols = st.columns(3)
    cols[0].metric("Flujo equivalente ATS" if not is_multilane else "Flujo equivalente por carril", _format(intermediate.get("speed_vp_pc_per_h", intermediate.get("adjusted_flow_pc_per_h_per_lane")), 1, "pc/h"))
    second_measure = intermediate.get("ptsf_vp_pc_per_h", intermediate.get("density_pc_per_km_per_lane"))
    cols[1].metric("Flujo equivalente PTSF" if not is_multilane else "Densidad por carril", _format(second_measure, 1, "pc/h" if not is_multilane else "pc/km/carril"))
    cols[2].metric("Velocidad media de viaje (ATS)", _format(final.get("average_travel_speed_km_per_h"), 1, "km/h"))
    cols = st.columns(3)
    cols[0].metric("Tiempo siguiendo (PTSF)", _format(final.get("percent_time_spent_following"), 1, "%"))
    other = final.get("other_performance_measures")
    if other:
        cols[1].metric("Vehículo-km en hora pico", _format(other.get("vehicle_km_peak_hour"), 1, "veh-km"))
        cols[2].metric("Tiempo total de viaje, 15 min pico", _format(other.get("travel_time_peak_15_min_veh_h"), 1, "veh-h"))

    st.subheader("7. NIVEL DE SERVICIO")
    st.metric("Clasificación LOS", str(final.get("level_of_service", "No calculado")))
    st.caption("La clasificación se muestra sin codificación cromática adicional.")

    st.subheader("8. ADVERTENCIAS")
    _render_warnings(messages, result)

    st.subheader("9. REFERENCIAS")
    st.write(f"**Fuente metodológica:** {metadata['methodological_source']}.")
    for reference in result.formula_references:
        st.markdown(f"- {reference}")
    st.caption("El mismo paquete de datos del informe puede utilizarse como entrada de un futuro generador PDF.")


def render_verification(
    table_checks: list[dict[str, Any]] | None,
    *,
    lookup_succeeded: bool | None,
) -> None:
    """Show the table availability checks performed before calculation."""
    st.header("Verificación de datos HCM")
    if table_checks is None:
        st.info("La verificación de tablas aparecerá después de un intento de cálculo válido.")
        return
    if table_checks:
        st.dataframe(table_checks, hide_index=True, width="stretch")
    if lookup_succeeded is True:
        st.success("El cálculo terminó y los parámetros requeridos se recuperaron.")
    elif lookup_succeeded is False:
        st.error("El cálculo no se completó o no se recuperó algún parámetro. Consulte las advertencias.")
    else:
        st.warning("No se ejecutó la búsqueda porque existen errores de validación.")


def render_warnings(
    messages: list[str] | tuple[str, ...] | None = None,
    result: CalculationResult | None = None,
) -> None:
    """Compatibility wrapper for showing warnings outside the report view."""
    st.header("Advertencias")
    _render_warnings(messages or (), result)


def _render_warnings(messages: list[str] | tuple[str, ...], result: CalculationResult | None) -> None:
    displayed = False
    for message in messages:
        st.warning(message)
        displayed = True
    if result:
        for warning in result.warnings:
            st.warning(warning)
            displayed = True
    if not displayed:
        st.info("No hay advertencias registradas.")


def _input_rows(result: CalculationResult, submitted: dict[str, Any]) -> list[dict[str, str]]:
    """Combine project metadata with the exact engine input snapshot."""
    labels = {
        "hourly_volume_veh_per_h": ("Volumen horario bidireccional", "veh/h"),
        "peak_hour_factor": ("PHF", "adimensional"),
        "major_direction_percent": ("Porcentaje en sentido de mayor flujo", "%"),
        "trucks_percent": ("Camiones y buses", "%"),
        "recreational_vehicles_percent": ("Vehículos recreacionales", "%"),
        "terrain": ("Terreno", ""), "highway_class": ("Clase HCM", ""),
        "segment_length_km": ("Longitud del segmento", "km"),
        "lane_width_m": ("Ancho de carril", "m"), "shoulder_width_m": ("Ancho de berma", "m"),
        "access_points_per_km": ("Densidad de accesos", "accesos/km"),
        "no_passing_zones_percent": ("Zonas de no rebase", "%"),
        "base_free_flow_speed_km_per_h": ("BFFS ingresada", "km/h"),
        "lanes_per_direction": ("Carriles por sentido", "carriles"),
        "lateral_clearance_m": ("Despeje lateral total", "m"),
        "median_type": ("Tipo de mediana", ""),
        "driver_population_factor": ("Factor población conductores fP", "adimensional"),
    }
    rows = []
    for section, fields in (("Proyecto", submitted.get("project", {})), ("Tipo de vía", submitted.get("facility", {}))):
        for key, value in fields.items():
            rows.append({"Dato": f"{section}: {key.replace('_', ' ')}", "Valor": _format(value), "Unidad": "", "Origen": "Entrada del usuario"})
    for key, value in result.inputs.items():
        label, unit = labels.get(key, (key.replace("_", " "), ""))
        rows.append({"Dato": label, "Valor": _format(value), "Unidad": unit, "Origen": "Entrada del usuario"})
    for section in ("operation", "procedure_additional"):
        for key, value in submitted.get(section, {}).items():
            if key in {"field_notes"}:
                rows.append({"Dato": key.replace("_", " "), "Valor": _format(value), "Unidad": "", "Origen": "Registro del usuario; no utilizado por el motor"})
    return rows


def _factor_rows(parameters: dict[str, Any], intermediate: dict[str, Any]) -> list[dict[str, str]]:
    """Present table-derived and calculated factors with source identification."""
    if "heavy_vehicle_factor" in parameters:
        multi_defs = (
            ("lane_width_adjustment_kmh", "fLW — ancho de carril", "km/h", "Tabla 15"),
            ("lateral_clearance_adjustment_kmh", "fLC — despeje lateral", "km/h", "Tabla 16"),
            ("median_adjustment_kmh", "fM — mediana", "km/h", "Tabla 17"),
            ("access_adjustment_kmh", "fA — accesos", "km/h", "Tabla 18"),
            ("heavy_vehicle_factor", "fHV — vehículos pesados", "adimensional", "Eq. vehículos pesados / Tabla 19"),
            ("truck_equivalency", "ET — camiones/buses", "adimensional", "Tabla 19"),
            ("recreational_vehicle_equivalency", "ER — recreacionales", "adimensional", "Tabla 19"),
            ("capacity_pc_per_h_per_lane", "Capacidad por carril", "pc/h/carril", "Tabla 14"),
        )
        return [{"Factor/Parámetro": label, "Valor": _format(parameters.get(key)), "Unidad": unit, "Fuente": source, "Tipo": "Tabla del documento proporcionado"} for key, label, unit, source in multi_defs]
    definitions = (
        ("free_flow_speed_adjustment_lane_shoulder_km_per_h", "fLS — carril/berma", "km/h", "Exhibit 20-5"),
        ("free_flow_speed_adjustment_access_km_per_h", "fA — accesos", "km/h", "Exhibit 20-6"),
        ("grade_adjustment_speed", "fG — ATS", "adimensional", "Exhibit 20-7"),
        ("heavy_vehicle_factor_speed", "fHV — ATS", "adimensional", "Eq. 20-4 / Exhibit 20-9"),
        ("truck_equivalency_speed", "ET — ATS", "adimensional", "Exhibit 20-9"),
        ("rv_equivalency_speed", "ER — ATS", "adimensional", "Exhibit 20-9"),
        ("grade_adjustment_ptsf", "fG — PTSF", "adimensional", "Exhibit 20-8"),
        ("heavy_vehicle_factor_ptsf", "fHV — PTSF", "adimensional", "Eq. 20-4 / Exhibit 20-10"),
        ("truck_equivalency_ptsf", "ET — PTSF", "adimensional", "Exhibit 20-10"),
        ("rv_equivalency_ptsf", "ER — PTSF", "adimensional", "Exhibit 20-10"),
        ("capacity_two_way_pc_per_h", "Capacidad bidireccional", "pc/h", "Capacidad documentada, Capítulo 20"),
        ("capacity_per_direction_pc_per_h", "Capacidad por sentido", "pc/h", "Capacidad documentada, Capítulo 20"),
    )
    rows = [{"Factor/Parámetro": label, "Valor": _format(parameters.get(key)), "Unidad": unit, "Fuente": source, "Tipo": "Tabla o parámetro HCM"} for key, label, unit, source in definitions]
    for key, label, unit, source in (
        ("fnp_adjustment_km_per_h", "fnp — zonas de no rebase", "km/h", "Exhibit 20-11"),
        ("fd_np_adjustment_percent", "fd/np — PTSF", "%", "Exhibit 20-12"),
    ):
        if key in intermediate:
            rows.append({"Factor/Parámetro": label, "Valor": _format(intermediate[key]), "Unidad": unit, "Fuente": source, "Tipo": "Valor tabulado/interpolado"})
    return rows


def _intermediate_rows(values: dict[str, Any]) -> list[dict[str, str]]:
    """Format all intermediate engine values without recalculating them."""
    units = {
        "free_flow_speed_km_per_h": "km/h", "speed_vp_pc_per_h": "pc/h",
        "adjusted_flow_pc_per_h_per_lane": "pc/h/carril",
        "density_pc_per_km_per_lane": "pc/km/carril",
        "speed_highest_direction_flow_pc_per_h": "pc/h", "ptsf_vp_pc_per_h": "pc/h",
        "ptsf_highest_direction_flow_pc_per_h": "pc/h", "average_travel_speed_km_per_h": "km/h",
        "base_ptsf_percent": "%", "fd_np_adjustment_percent": "%",
        "percent_time_spent_following": "%", "fnp_adjustment_km_per_h": "km/h",
        "volume_capacity_ratio": "adimensional",
    }
    return [{"Resultado intermedio": key.replace("_", " "), "Valor": _format(value), "Unidad": units.get(key, ""), "Origen": "Motor de cálculo HCM"} for key, value in values.items()]


def _procedure_rows(result: CalculationResult) -> list[dict[str, str]]:
    """List the equations and criteria documented by the integrated procedure."""
    inputs, parameters, intermediate, final = result.inputs, result.parameters, result.intermediate_results, result.final_results
    if "lanes_per_direction" in inputs:
        return [
            _step("Velocidad a flujo libre", "FFS = BFFS − fLW − fLC − fM − fA", "BFFS, ajustes geométricos, mediana y accesos en tabla Factores HCM", intermediate["free_flow_speed_km_per_h"], "C05-C07-Capacidad_2.pdf, Tablas 15-18", "km/h"),
            _step("Factor de vehículos pesados", "fHV = 1 / [1 + PT(ET−1) + PR(ER−1)]", "Porcentajes de camiones/RV y equivalencias según terreno", parameters["heavy_vehicle_factor"], "Tabla 19 del documento proporcionado", "adimensional"),
            _step("Flujo equivalente por carril", "vp = VHD / (PHF × N × fHV × fP)", f"VHD direccional={intermediate['directional_volume_veh_per_h']}; PHF={inputs['peak_hour_factor']}; N={inputs['lanes_per_direction']}; fHV={parameters['heavy_vehicle_factor']}; fP={inputs['driver_population_factor']}", intermediate["adjusted_flow_pc_per_h_per_lane"], "Sección 3.6", "pc/h/carril"),
            _step("Velocidad de operación", "Interpolación lineal entre puntos tabulados de flujo y velocidad", "Tabla 14 según la banda FFS", intermediate.get("operating_speed_km_per_h"), "Tabla 14 del documento proporcionado", "km/h"),
            _step("Densidad", "D = vp / S", f"vp={intermediate['adjusted_flow_pc_per_h_per_lane']}; S={intermediate.get('operating_speed_km_per_h')}", intermediate.get("density_pc_per_km_per_lane"), "Sección 3.3", "pc/km/carril"),
            _step("Nivel de servicio", "Comparar densidad y flujo con los límites de Tabla 14", f"Banda FFS={parameters['criteria_ffs_band_km_per_h']}; densidad={intermediate.get('density_pc_per_km_per_lane')}", final.get("level_of_service"), "Tabla 14 del documento proporcionado", ""),
        ]
    rows = [
        _step("Ajuste geométrico", "FFS = BFFS − fLS − fA", f"BFFS={inputs['base_free_flow_speed_km_per_h']}; fLS={parameters['free_flow_speed_adjustment_lane_shoulder_km_per_h']}; fA={parameters['free_flow_speed_adjustment_access_km_per_h']}", intermediate["free_flow_speed_km_per_h"], "Eq. 20-2; Exhibits 20-5/20-6", "km/h"),
        _step("Flujo equivalente ATS", "vp = V / (PHF · fG · fHV)", f"V={inputs['hourly_volume_veh_per_h']}; PHF={inputs['peak_hour_factor']}; fG={parameters['grade_adjustment_speed']}; fHV={parameters['heavy_vehicle_factor_speed']}", intermediate["speed_vp_pc_per_h"], "Eq. 20-3; Exhibit 20-7", "pc/h"),
        _step("Flujo equivalente PTSF", "vp = V / (PHF · fG · fHV)", f"V={inputs['hourly_volume_veh_per_h']}; PHF={inputs['peak_hour_factor']}; fG={parameters['grade_adjustment_ptsf']}; fHV={parameters['heavy_vehicle_factor_ptsf']}", intermediate["ptsf_vp_pc_per_h"], "Eq. 20-3; Exhibit 20-8", "pc/h"),
        _step("Relación volumen/capacidad", "v/c = vp / c", f"vp={intermediate['speed_vp_pc_per_h']}; c={parameters['capacity_two_way_pc_per_h']}", final["volume_capacity_ratio"], "Eq. 20-8 / worksheet HCM", "adimensional"),
    ]
    for name, formula, output, source, unit in (
        ("ATS", "ATS = FFS − 0.0125vp − fnp", "average_travel_speed_km_per_h", "Eq. 20-5; Exhibit 20-11", "km/h"),
        ("PTSF base", "BPTSF = 100[1 − exp(−0.000879vp)]", "base_ptsf_percent", "Eq. 20-7", "%"),
        ("PTSF ajustado", "PTSF = BPTSF + fd/np", "percent_time_spent_following", "Eq. 20-6; Exhibit 20-12", "%"),
    ):
        if output in intermediate:
            rows.append(_step(name, formula, f"Entradas y parámetros según tabla Factores/Cálculos intermedios", intermediate[output], source, unit))
    rows.append(_step("Nivel de servicio", "Criterios de LOS según clase de carretera", f"Clase={inputs['highway_class']}; ATS={intermediate.get('average_travel_speed_km_per_h')}; PTSF={intermediate.get('percent_time_spent_following')}", final.get("level_of_service"), "Exhibits 20-2/20-4", ""))
    return rows


def _step(name: str, equation: str, values: str, output: Any, reference: str, unit: str) -> dict[str, str]:
    return {"Etapa": name, "Ecuación/criterio": equation, "Valores utilizados": values, "Resultado": _format(output, 4, unit), "Referencia": reference}


def _format(value: Any, digits: int = 3, unit: str = "") -> str:
    if value is None:
        return "No calculado"
    if isinstance(value, float):
        return f"{value:,.{digits}f} {unit}".strip()
    return f"{value} {unit}".strip()


def _safe_filename(project: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in project).strip("_")
    return cleaned or datetime.now().strftime("%Y%m%d")
