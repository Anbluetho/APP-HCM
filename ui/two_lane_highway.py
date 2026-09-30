"""Compact input components for the HCM 2000 two-lane procedure."""

import streamlit as st

from models.input_data import (
    FacilityInfo,
    GeometricInputs,
    OperationalInputs,
    ProcedureInputs,
    ProjectInfo,
    TrafficInputs,
)
from models.specific_grade import SpecificGradeInputs


def render_analysis_type() -> str:
    """Select between the existing two-way procedure and specific grades."""
    st.subheader("Tipo de análisis")
    return st.radio(
        "Seleccione el procedimiento HCM 2000",
        ["Segmento bidireccional extendido", "Pendiente específica"],
        key="analysis_type",
    )


def render_project_info() -> ProjectInfo:
    """Collect required project identification and optional report metadata."""
    st.subheader("Información del proyecto")
    left, right = st.columns(2)
    with left:
        project_name = st.text_input("Proyecto *", key="project_name")
    with right:
        location = st.text_input("Ubicación del tramo *", key="project_location")
    with st.expander("Metadatos opcionales"):
        analyst = st.text_input("Responsable", key="analyst")
        data_origin = st.selectbox(
            "Origen de los datos",
            ["Aforo de campo", "Base secundaria", "Información suministrada"],
            key="data_origin",
        )
    return {
        "project_name": project_name,
        "analyst": analyst,
        "location": location,
        "data_origin": data_origin,
    }


def render_facility_selection() -> FacilityInfo:
    """Identify the single facility type currently supported by this page."""
    st.markdown("**Tipo de vía:** Carretera de dos carriles")
    return {"facility_type": "Carretera de dos carriles"}


def render_geometric_inputs() -> GeometricInputs:
    """Collect segment geometry in two columns."""
    st.subheader("Datos geométricos")
    left, right = st.columns(2)
    with left:
        segment_length = st.number_input(
            "Longitud del tramo (km) *",
            min_value=0.0,
            value=None,
            step=0.1,
            placeholder="Mayor o igual que 3 km",
            key="segment_length_km",
        )
        lane_width = st.number_input(
            "Ancho de carril (m) *",
            min_value=0.0,
            value=None,
            step=0.1,
            placeholder="Ancho medido",
            key="lane_width_m",
        )
    with right:
        shoulder_width = st.number_input(
            "Ancho de berma/banquina (m) *",
            min_value=0.0,
            value=None,
            step=0.1,
            placeholder="Ancho medido",
            key="shoulder_width_m",
        )
        st.number_input(
            "Zona donde no se permite adelantar (%) *",
            min_value=0.0,
            max_value=100.0,
            value=None,
            step=1.0,
            key="no_passing_zones_percent",
        )
    return {
        "segment_length_km": segment_length,
        "lane_width_m": lane_width,
        "shoulder_width_m": shoulder_width,
        "lanes_per_direction": None,
        "lateral_clearance_m": None,
        "median_type": None,
    }


def render_traffic_inputs() -> TrafficInputs:
    """Collect traffic inputs in two columns with units in each label."""
    st.subheader("Datos de tránsito")
    left, right = st.columns(2)
    with left:
        hourly_volume = st.number_input(
            "Volumen horario bidireccional (veh/h) *",
            min_value=0.0,
            value=None,
            step=1.0,
            key="hourly_volume_two_way",
        )
        phf = st.number_input(
            "Factor de hora pico, PHF *",
            min_value=0.0,
            max_value=1.0,
            value=None,
            step=0.01,
            key="peak_hour_factor",
        )
        major_split_choice = st.selectbox(
            "Distribución direccional (mayor/opuesto) *",
            ["Seleccione...", 50, 60, 70, 80, 90],
            format_func=lambda value: (
                "Seleccione la distribución"
                if value == "Seleccione..."
                else f"{value}/{100-int(value)}"
            ),
            key="major_direction_split",
        )
    with right:
        trucks_percent = st.number_input(
            "Camiones y buses (%) *",
            min_value=0.0,
            max_value=100.0,
            value=None,
            step=0.1,
            key="trucks_percent",
        )
        rvs_percent = st.number_input(
            "Vehículos recreacionales, RV (%) *",
            min_value=0.0,
            max_value=100.0,
            value=None,
            step=0.1,
            key="recreational_vehicles_percent",
        )
    return {
        "hourly_volume_two_way_veh_per_h": hourly_volume,
        "peak_hour_factor": phf,
        "major_direction_percent": (
            None if major_split_choice == "Seleccione..." else int(major_split_choice)
        ),
        "trucks_percent": trucks_percent,
        "recreational_vehicles_percent": rvs_percent,
    }


def render_operational_inputs() -> OperationalInputs:
    """Collect terrain and HCM road class, required by the existing analyzer."""
    st.subheader("Condiciones de operación")
    left, right = st.columns(2)
    with left:
        terrain_choice = st.selectbox(
            "Tipo de terreno *",
            ["Seleccione...", "plano", "ondulado", "montanoso", "escarpado"],
            format_func=lambda value: {
                "Seleccione...": "Seleccione el terreno",
                "plano": "Plano",
                "ondulado": "Ondulado",
                "montanoso": "Montañoso",
                "escarpado": "Escarpado",
            }[value],
            key="terrain",
        )
    with right:
        highway_class_choice = st.selectbox(
            "Clase de carretera HCM *",
            ["Seleccione...", "I", "II", "III"],
            format_func=lambda value: (
                "Seleccione la clase"
                if value == "Seleccione..."
                else f"Clase {value}"
            ),
            key="highway_class",
        )
    return {
        "terrain": None if terrain_choice == "Seleccione..." else terrain_choice,
        "highway_class": (
            None if highway_class_choice == "Seleccione..." else highway_class_choice
        ),
    }


def render_procedure_inputs() -> ProcedureInputs:
    """Collect additional variables required by the implemented HCM procedure."""
    st.subheader("Datos adicionales del procedimiento")
    left, right = st.columns(2)
    with left:
        access_points = st.number_input(
            "Densidad de puntos de acceso (accesos/km) *",
            min_value=0.0,
            value=None,
            step=1.0,
            key="access_points_per_km",
            help="Use una categoría documentada: 0, 6, 12, 18 o al menos 24 accesos/km.",
        )
    with right:
        bffs = st.number_input(
            "Velocidad base a flujo libre, BFFS (km/h) *",
            min_value=0.0,
            value=None,
            step=1.0,
            key="base_free_flow_speed_km_per_h",
            help="Ingrese la velocidad base sustentada por los datos del proyecto.",
        )
    no_passing = st.session_state.get("no_passing_zones_percent")
    return {
        "field_notes": "",
        "access_points_per_km": access_points,
        "no_passing_zones_percent": no_passing,
        "base_free_flow_speed_km_per_h": bffs,
        "driver_population_factor": None,
    }


def render_specific_grade_inputs() -> SpecificGradeInputs:
    """Collect only the inputs used by the specific-grade directional engine."""
    st.subheader("Datos de la pendiente y sentido")
    direction_label = st.radio(
        "Pendiente en el sentido analizado *",
        ["Ascenso", "Descenso"],
        key="specific_grade_direction",
        horizontal=True,
    )
    direction = "upgrade" if direction_label == "Ascenso" else "downgrade"
    left, right = st.columns(2)
    with left:
        grade_percent = st.number_input(
            "Pendiente (%) *", min_value=0.0, value=None, step=0.1,
            key="specific_grade_percent",
        )
        grade_length = st.number_input(
            "Longitud de la pendiente (km) *", min_value=0.0, value=None,
            step=0.1, key="specific_grade_length_km",
        )
    with right:
        highway_class = st.selectbox(
            "Clase HCM *", ["Seleccione...", "I", "II"],
            format_func=lambda value: "Seleccione la clase" if value == "Seleccione..." else f"Clase {value}",
            key="specific_grade_highway_class",
        )
        no_passing = st.number_input(
            "Zonas de no rebase en el sentido analizado (%) *",
            min_value=0.0, max_value=100.0, value=None, step=1.0,
            key="specific_grade_no_passing_percent",
        )

    st.subheader("Datos de tránsito por sentido")
    left, right = st.columns(2)
    with left:
        analysis_volume = st.number_input(
            "Volumen del sentido analizado (veh/h) *", min_value=0.0,
            value=None, step=1.0, key="specific_grade_analysis_volume",
        )
        analysis_trucks = st.number_input(
            "Camiones y buses, sentido analizado (%) *", min_value=0.0,
            max_value=100.0, value=None, step=0.1,
            key="specific_grade_analysis_trucks",
        )
        analysis_rvs = st.number_input(
            "RV, sentido analizado (%) *", min_value=0.0, max_value=100.0,
            value=None, step=0.1, key="specific_grade_analysis_rvs",
        )
    with right:
        opposing_volume = st.number_input(
            "Volumen del sentido opuesto (veh/h) *", min_value=0.0,
            value=None, step=1.0, key="specific_grade_opposing_volume",
        )
        opposing_trucks = st.number_input(
            "Camiones y buses, sentido opuesto (%) *", min_value=0.0,
            max_value=100.0, value=None, step=0.1,
            key="specific_grade_opposing_trucks",
        )
        opposing_rvs = st.number_input(
            "RV, sentido opuesto (%) *", min_value=0.0, max_value=100.0,
            value=None, step=0.1, key="specific_grade_opposing_rvs",
        )
    phf = st.number_input(
        "Factor de hora pico, PHF *", min_value=0.0, max_value=1.0,
        value=None, step=0.01, key="specific_grade_phf",
    )

    st.subheader("Geometría para determinar FFS")
    left, right = st.columns(2)
    with left:
        lane_width = st.number_input(
            "Ancho de carril (m) *", min_value=0.0, value=None, step=0.1,
            key="specific_grade_lane_width",
        )
        access_density = st.number_input(
            "Puntos de acceso (accesos/km) *", min_value=0.0, value=None,
            step=1.0, key="specific_grade_access_points",
            help="Exhibit 20-6 usa las categorías 0, 6, 12, 18 o ≥24 por km.",
        )
    with right:
        shoulder_width = st.number_input(
            "Ancho de berma (m) *", min_value=0.0, value=None, step=0.1,
            key="specific_grade_shoulder_width",
        )
        bffs_analysis = st.number_input(
            "BFFS del sentido analizado (km/h) *", min_value=0.0,
            value=None, step=1.0, key="specific_grade_bffs_analysis",
            help="Dato de campo/proyecto; no se asigna un valor HCM por defecto.",
        )

    downhill_crawl_choice = st.selectbox(
        "¿Hay camiones a velocidad de arrastre en el sentido descendente? *",
        ["Seleccione...", "No", "Sí"], key="specific_grade_crawl_condition",
        help="La opción Sí activa la ecuación 20-14 y requiere datos de Exhibit 20-18.",
    )
    crawl_condition = None if downhill_crawl_choice == "Seleccione..." else downhill_crawl_choice == "Sí"
    crawl_share = None
    crawl_speed = None
    bffs_opposing = None
    if crawl_condition:
        crawl_share = st.number_input(
            "Camiones a velocidad de arrastre (% de camiones del sentido descendente) *",
            min_value=0.0, max_value=100.0, value=None, step=0.1,
            key="specific_grade_crawl_truck_share",
        )
        crawl_speed = st.number_input(
            "Velocidad de arrastre de camiones (km/h) *", min_value=0.0,
            value=None, step=1.0, key="specific_grade_crawl_speed",
        )
        if direction == "upgrade":
            bffs_opposing = st.number_input(
                "BFFS del sentido descendente/opuesto (km/h) *",
                min_value=0.0, value=None, step=1.0,
                key="specific_grade_bffs_opposing",
                help="Solo se solicita porque la condición de arrastre aplica al descenso opuesto.",
            )

    return SpecificGradeInputs(
        analysis_grade_direction=direction,
        grade_percent=grade_percent,
        grade_length_km=grade_length,
        analysis_volume_veh_per_h=analysis_volume,
        opposing_volume_veh_per_h=opposing_volume,
        peak_hour_factor=phf,
        analysis_trucks_percent=analysis_trucks,
        analysis_rvs_percent=analysis_rvs,
        opposing_trucks_percent=opposing_trucks,
        opposing_rvs_percent=opposing_rvs,
        highway_class="" if highway_class == "Seleccione..." else highway_class,
        lane_width_m=lane_width,
        shoulder_width_m=shoulder_width,
        access_points_per_km=access_density,
        no_passing_zones_percent=no_passing,
        base_free_flow_speed_analysis_km_per_h=bffs_analysis,
        downhill_crawl_condition=crawl_condition,
        downhill_trucks_at_crawl_percent=crawl_share,
        downhill_truck_crawl_speed_km_per_h=crawl_speed,
        base_free_flow_speed_opposing_km_per_h=bffs_opposing,
    )
