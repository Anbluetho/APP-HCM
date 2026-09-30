"""Compact presentation of two-lane HCM analysis results."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from models.calculation_result import CalculationResult
from reports.csv_export import report_to_csv
from reports.report_data import build_report_payload


_UNITS = {
    "average_travel_speed_km_per_h": "km/h",
    "percent_time_spent_following": "%",
    "capacity_two_way_pc_per_h": "pc/h",
    "capacity_per_direction_pc_per_h": "pc/h",
    "speed_vp_pc_per_h": "pc/h",
    "ptsf_vp_pc_per_h": "pc/h",
    "free_flow_speed_km_per_h": "km/h",
    "fnp_adjustment_km_per_h": "km/h",
    "fd_np_adjustment_percent": "%",
    "volume_capacity_ratio": "adimensional",
    "analysis_flow_ats_pc_per_h": "pc/h",
    "opposing_flow_ats_pc_per_h": "pc/h",
    "analysis_flow_ptsf_pc_per_h": "pc/h",
    "opposing_flow_ptsf_pc_per_h": "pc/h",
    "capacity_pc_per_h_direction": "pc/h",
}


def render_results(
    result: CalculationResult | None,
    submitted_inputs: dict[str, Any] | None = None,
    messages: list[str] | tuple[str, ...] = (),
    *,
    table_checks: list[dict[str, Any]] | None = None,
    lookup_succeeded: bool | None = None,
) -> None:
    """Show key performance measures first and move audit details to an expander."""
    if result is None:
        if messages:
            st.subheader("Validación y advertencias")
            for message in messages:
                st.error(message)
        return

    final = result.final_results
    inputs = result.inputs
    submitted_inputs = submitted_inputs or {}
    level = str(final.get("level_of_service", "No calculado"))
    speed = final.get("average_travel_speed_km_per_h")
    following = final.get("percent_time_spent_following")
    capacity = final.get("capacity_pc_per_h_two_way")
    demand = inputs.get("hourly_volume_veh_per_h")

    st.divider()
    st.subheader("Resultado")
    st.metric("NIVEL DE SERVICIO (LOS)", level)

    metric_columns = st.columns(4)
    metric_columns[0].metric("Velocidad promedio", _format(speed, 1, "km/h"))
    metric_columns[1].metric("Tiempo siguiendo", _format(following, 1, "%"))
    metric_columns[2].metric("Capacidad bidireccional", _format(capacity, 0, "pc/h"))
    metric_columns[3].metric("Demanda analizada", _format(demand, 0, "veh/h"))

    summary = [
        {"Parámetro": "Velocidad promedio", "Resultado": _format(speed, 1), "Unidad": "km/h"},
        {"Parámetro": "Tiempo siguiendo vehículos", "Resultado": _format(following, 1), "Unidad": "%"},
        {"Parámetro": "Capacidad bidireccional", "Resultado": _format(capacity, 0), "Unidad": "pc/h"},
        {"Parámetro": "Demanda analizada", "Resultado": _format(demand, 0), "Unidad": "veh/h"},
        {"Parámetro": "Nivel de Servicio", "Resultado": level, "Unidad": "—"},
    ]
    st.dataframe(summary, hide_index=True, width="stretch")

    if messages or result.warnings:
        with st.expander("Advertencias", expanded=True):
            for message in messages:
                st.warning(message)
            for warning in result.warnings:
                st.warning(warning)

    with st.expander("Ver detalle del cálculo"):
        st.markdown("**Datos utilizados**")
        st.dataframe(_input_rows(result, submitted_inputs), hide_index=True, width="stretch")

        st.markdown("**Factores HCM y parámetros recuperados**")
        st.dataframe(_value_rows(result.parameters, "Parámetro HCM"), hide_index=True, width="stretch")

        st.markdown("**Resultados intermedios**")
        st.dataframe(_value_rows(result.intermediate_results, "Cálculo intermedio"), hide_index=True, width="stretch")

        st.markdown("**Referencias metodológicas**")
        if result.formula_references:
            for reference in result.formula_references:
                st.markdown(f"- {reference}")
        else:
            st.caption("El motor no proporcionó referencias adicionales para este resultado.")

        st.markdown("**Verificación de tablas**")
        if table_checks is not None:
            if table_checks:
                st.dataframe(table_checks, hide_index=True, width="stretch")
            if lookup_succeeded is True:
                st.success("Se encontraron los parámetros requeridos para el cálculo.")
            else:
                st.error("No se completó la verificación de todos los parámetros requeridos.")
        else:
            st.caption("No hay una verificación de tablas asociada a este resultado.")

        payload = build_report_payload(submitted_inputs, result)
        project = payload["metadata"].get("project") or "analisis"
        st.download_button(
            "Descargar resultados CSV",
            data=report_to_csv(payload),
            file_name=f"informe_hcm_{_safe_filename(project)}.csv",
            mime="text/csv; charset=utf-8",
            key="download_hcm_report_csv",
        )


def render_specific_grade_results(
    result: CalculationResult | None,
    messages: list[str] | tuple[str, ...] = (),
    *,
    table_checks: list[dict[str, Any]] | None = None,
    lookup_succeeded: bool | None = None,
) -> None:
    """Present directional specific-grade results without recalculating them."""
    if result is None:
        if messages:
            st.subheader("Validación y advertencias")
            for message in messages:
                st.error(message)
        return

    final = result.final_results
    st.divider()
    st.subheader("Resultado de pendiente específica")
    st.metric("NIVEL DE SERVICIO (LOS)", str(final.get("level_of_service", "No calculado")))
    columns = st.columns(4)
    columns[0].metric("ATS direccional", _format(final.get("average_travel_speed_km_per_h"), 1, "km/h"))
    columns[1].metric("PTSF direccional", _format(final.get("percent_time_spent_following"), 1, "%"))
    columns[2].metric("Capacidad por sentido", _format(final.get("capacity_pc_per_h_direction"), 0, "pc/h"))
    columns[3].metric("v/c direccional", _format(final.get("volume_capacity_ratio"), 3))

    flow_rows = [
        {"Medida": "ATS", "vd analizado": _format(final.get("analysis_flow_ats_pc_per_h"), 1), "vo opuesto": _format(final.get("opposing_flow_ats_pc_per_h"), 1), "Unidad": "pc/h"},
        {"Medida": "PTSF", "vd analizado": _format(final.get("analysis_flow_ptsf_pc_per_h"), 1), "vo opuesto": _format(final.get("opposing_flow_ptsf_pc_per_h"), 1), "Unidad": "pc/h"},
    ]
    st.dataframe(flow_rows, hide_index=True, width="stretch")

    if messages or result.warnings:
        with st.expander("Advertencias", expanded=True):
            for message in messages:
                st.warning(message)
            for warning in result.warnings:
                st.warning(warning)

    with st.expander("Ver detalle del cálculo"):
        st.markdown("**Datos de entrada**")
        st.dataframe(_value_rows(result.inputs, "Dato ingresado"), hide_index=True, width="stretch")

        st.markdown("**Factores HCM por medida y sentido**")
        st.dataframe(_value_rows(result.parameters, "Tabla/factor HCM"), hide_index=True, width="stretch")

        st.markdown("**Iteraciones y resultados intermedios**")
        iteration_records = result.intermediate_results.get("flow_iterations", {})
        scalar_intermediates = {
            key: value for key, value in result.intermediate_results.items()
            if key != "flow_iterations"
        }
        st.dataframe(_value_rows(scalar_intermediates, "Cálculo intermedio"), hide_index=True, width="stretch")
        if isinstance(iteration_records, dict):
            for route, records in iteration_records.items():
                st.markdown(f"**Iteración {route.replace('_', ' ').upper()}**")
                st.dataframe(records, hide_index=True, width="stretch")

        st.markdown("**Referencias metodológicas**")
        for reference in result.formula_references:
            st.markdown(f"- {reference}")

        st.markdown("**Verificación de tablas**")
        if table_checks is not None:
            st.dataframe(table_checks, hide_index=True, width="stretch")
            if lookup_succeeded:
                st.success("Se encontraron las tablas y parámetros requeridos.")
            else:
                st.error("No se completó la verificación de todos los parámetros requeridos.")


def _input_rows(
    result: CalculationResult, submitted: dict[str, Any]
) -> list[dict[str, str]]:
    """Prepare a concise audit table of project information and engine inputs."""
    labels = {
        "hourly_volume_veh_per_h": ("Volumen horario", "veh/h"),
        "peak_hour_factor": ("Factor de hora pico (PHF)", "adimensional"),
        "major_direction_percent": ("Distribución direccional mayor/opuesto", "% / %"),
        "trucks_percent": ("Camiones y buses", "%"),
        "recreational_vehicles_percent": ("Vehículos recreacionales", "%"),
        "terrain": ("Tipo de terreno", ""),
        "highway_class": ("Clase de carretera HCM", ""),
        "segment_length_km": ("Longitud del tramo", "km"),
        "lane_width_m": ("Ancho de carril", "m"),
        "shoulder_width_m": ("Ancho de berma/banquina", "m"),
        "access_points_per_km": ("Densidad de puntos de acceso", "accesos/km"),
        "no_passing_zones_percent": ("Zonas donde no se permite adelantar", "%"),
        "base_free_flow_speed_km_per_h": ("Velocidad base a flujo libre (BFFS)", "km/h"),
    }
    rows: list[dict[str, str]] = []
    project = submitted.get("project", {})
    for key, label in (("project_name", "Proyecto"), ("location", "Ubicación"), ("analyst", "Responsable")):
        value = project.get(key)
        if value:
            rows.append({"Dato": label, "Valor": str(value), "Unidad": "", "Origen": "Usuario"})
    for key, value in result.inputs.items():
        label, unit = labels.get(key, (key.replace("_", " "), ""))
        rows.append(
            {"Dato": label, "Valor": _format(value), "Unidad": unit, "Origen": "Usuario"}
        )
    return rows


def _value_rows(values: dict[str, Any], origin: str) -> list[dict[str, str]]:
    """Format a dictionary of engine-produced values without recalculating it."""
    return [
        {
            "Variable": key.replace("_", " "),
            "Valor": _format(value),
            "Unidad": _UNITS.get(key, ""),
            "Tipo": origin,
        }
        for key, value in values.items()
    ]


def _format(value: Any, digits: int = 3, unit: str = "") -> str:
    """Format numeric results while keeping unavailable values explicit."""
    if value is None:
        return "No calculado"
    if isinstance(value, float):
        return f"{value:,.{digits}f} {unit}".strip()
    return f"{value} {unit}".strip()


def _safe_filename(project: str) -> str:
    """Convert a project label to a filesystem-safe report suffix."""
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in project).strip("_")
    return cleaned or datetime.now().strftime("%Y%m%d")
