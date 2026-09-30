"""Input components for the HCM highway analysis interface."""

import streamlit as st

from models.input_data import (
    FacilityInfo,
    GeometricInputs,
    OperationalInputs,
    ProcedureInputs,
    ProjectInfo,
    TrafficInputs,
)


def render_project_info() -> ProjectInfo:
    """Render project traceability fields and return their structured values."""
    with st.container(border=True):
        st.header("1. Información del proyecto", divider="gray")
        st.caption("Estos datos identifican el análisis; no modifican el resultado matemático.")
        left, right = st.columns(2)
        with left:
            project_name = st.text_input("Nombre del proyecto *", key="project_name")
            location = st.text_input("Ubicación del tramo *", key="project_location")
        with right:
            analyst = st.text_input(
                "Responsable del análisis",
                key="analyst",
                help="Se incluye en los metadatos del informe; no interviene en el cálculo.",
            )
            data_origin = st.selectbox(
                "Origen principal de los datos",
                ["Aforo de campo", "Base secundaria", "Información suministrada"],
                key="data_origin",
                help="Se conserva como trazabilidad del informe y no como variable del motor.",
            )
    return {
        "project_name": project_name,
        "analyst": analyst,
        "location": location,
        "data_origin": data_origin,
    }


def render_facility_selection() -> FacilityInfo:
    """Render the supported facility selection."""
    with st.container(border=True):
        st.header("2. Selección del tipo de vía", divider="gray")
        facility_type = st.selectbox(
            "Tipo de instalación",
            ["Carretera de dos carriles", "Carretera multicarril"],
            key="facility_type",
            help="El formulario y motor se adaptan al procedimiento elegido.",
        )
    return {"facility_type": facility_type}


def render_geometric_inputs() -> GeometricInputs:
    """Render geometric inputs required by the selected facility procedure."""
    multilane = st.session_state.get("facility_type") == "Carretera multicarril"
    with st.container(border=True):
        st.header("3. Datos geométricos", divider="gray")
        st.caption("Ingrese las características medidas del segmento analizado.")
        left, right = st.columns(2)
        with left:
            segment_length = None
            if not multilane:
                segment_length = st.number_input(
                    "Longitud del tramo (km) *", min_value=0.0, value=None,
                    step=0.1, placeholder="Ingrese un valor mayor que cero",
                    key="segment_length_km",
                    help="Se utiliza en el procedimiento de dos carriles para las medidas de desempeño del segmento.",
                )
            lane_width = st.number_input(
                "Ancho de carril (m) *",
                min_value=3.0 if multilane else 2.7,
                value=None,
                step=0.1,
                placeholder="Ingrese el ancho medido",
                key="lane_width_m",
            )
        with right:
            shoulder_width = None
            lanes_per_direction = None
            lateral_clearance = None
            median_type = None
            if multilane:
                lanes_per_direction = st.selectbox(
                    "Carriles por sentido *", ["Seleccione...", 2, 3],
                    format_func=lambda value: "Seleccione..." if value == "Seleccione..." else str(value),
                    key="lanes_per_direction",
                )
                lateral_clearance = st.number_input(
                    "Despeje lateral total (m) *", min_value=0.0, max_value=3.6,
                    value=None, step=0.1, key="lateral_clearance_m",
                    help="La tabla transcrita documenta valores de 0 a 3,6 m; se interpola dentro de ese rango.",
                )
                median_type = st.selectbox(
                    "Tipo de mediana *", ["Seleccione...", "divided", "undivided"],
                    format_func=lambda value: {
                        "Seleccione...": "Seleccione una opción",
                        "divided": "Vía dividida",
                        "undivided": "Vía no dividida",
                    }[value],
                    key="median_type",
                )
            else:
                shoulder_width = st.number_input(
                    "Ancho de berma (m) *", min_value=0.0, value=None,
                    step=0.1, placeholder="Ingrese el ancho medido", key="shoulder_width_m",
                )
    return {
        "segment_length_km": segment_length,
        "lane_width_m": lane_width,
        "shoulder_width_m": shoulder_width,
        "lanes_per_direction": None if lanes_per_direction in (None, "Seleccione...") else int(lanes_per_direction),
        "lateral_clearance_m": lateral_clearance,
        "median_type": None if median_type in (None, "Seleccione...") else median_type,
    }


def render_traffic_inputs() -> TrafficInputs:
    """Render observed demand, peak-hour, direction, and vehicle mix inputs."""
    with st.container(border=True):
        st.header("4. Datos de tránsito", divider="gray")
        st.caption("Use datos del mismo período de análisis y documente su procedencia en la sección del proyecto.")
        hourly_volume = st.number_input(
            "Volumen horario total de ambos sentidos (veh/h) *",
            min_value=0.0, value=None, step=1.0,
            placeholder="Ingrese el volumen horario observado",
            key="hourly_volume_two_way",
        )
        left, right = st.columns(2)
        with left:
            phf = st.number_input(
                "Factor de hora pico, PHF *", min_value=0.0, max_value=1.0,
                value=None, step=0.01,
                placeholder="Ingrese el valor observado o calculado",
                key="peak_hour_factor",
                help="Factor adimensional de hora pico del período analizado.",
            )
            major_split_choice = st.selectbox(
                "Distribución direccional (sentido de mayor flujo / opuesto) *",
                ["Seleccione...", 50, 60, 70, 80, 90],
                format_func=lambda value: "Seleccione la distribución" if value == "Seleccione..." else f"{value}/{100-int(value)}",
                key="major_direction_split",
            )
        with right:
            trucks_percent = st.number_input(
                "Camiones y buses (%) *", min_value=0.0, max_value=100.0,
                value=None, step=0.1, key="trucks_percent",
            )
            rvs_percent = st.number_input(
                "Vehículos recreacionales, RV (%) *", min_value=0.0, max_value=100.0,
                value=None, step=0.1, key="recreational_vehicles_percent",
            )
            st.caption("Camiones/buses + RV no debe superar el 100% del flujo.")
    return {
        "hourly_volume_two_way_veh_per_h": hourly_volume,
        "peak_hour_factor": phf,
        "major_direction_percent": None if major_split_choice == "Seleccione..." else int(major_split_choice),
        "trucks_percent": trucks_percent,
        "recreational_vehicles_percent": rvs_percent,
    }


def render_operational_inputs() -> OperationalInputs:
    """Render terrain and road-class inputs used by the selected procedure."""
    multilane = st.session_state.get("facility_type") == "Carretera multicarril"
    with st.container(border=True):
        st.header("5. Condiciones de operación", divider="gray")
        left, right = st.columns(2)
        with left:
            terrain_choice = st.selectbox(
                "Tipo de terreno *",
                ["Seleccione...", "plano", "ondulado", "montanoso", "escarpado"],
                format_func=lambda value: {
                    "Seleccione...": "Seleccione el terreno",
                    "plano": "Plano", "ondulado": "Ondulado",
                    "montanoso": "Montañoso", "escarpado": "Escarpado",
                }[value],
                key="terrain",
            )
        with right:
            highway_class_choice = None
            if not multilane:
                highway_class_choice = st.selectbox(
                    "Clase de carretera HCM *", ["Seleccione...", "I", "II", "III"],
                    format_func=lambda value: "Seleccione la clase" if value == "Seleccione..." else f"Clase {value}",
                    key="highway_class",
                )
            else:
                st.caption("Para el procedimiento multicarril, el LOS se determina mediante densidad.")
    return {
        "terrain": None if terrain_choice == "Seleccione..." else terrain_choice,
        "highway_class": None if highway_class_choice in (None, "Seleccione...") else highway_class_choice,
    }


def render_procedure_inputs() -> ProcedureInputs:
    """Render the additional inputs specific to the chosen HCM procedure."""
    multilane = st.session_state.get("facility_type") == "Carretera multicarril"
    with st.container(border=True):
        st.header("6. Datos adicionales del procedimiento", divider="gray")
        st.caption(
            "Procedimiento multicarril documentado en C05-C07-Capacidad_2.pdf, sección 3."
            if multilane else
            "Procedimiento operacional de segmento bidireccional, HCM 2000, capítulo 20."
        )
        left, right = st.columns(2)
        with left:
            access_points = st.number_input(
                "Densidad de puntos de acceso (accesos/km) *",
                min_value=0.0, value=None, step=1.0,
                help="Exhibit 20-6 contiene las categorías disponibles para el procedimiento de dos carriles.",
                key="access_points_per_km",
            )
            bffs = st.number_input(
                "Velocidad base a flujo libre, BFFS (km/h) *",
                min_value=70.0, max_value=110.0, value=None, step=1.0,
                placeholder="Ingrese la velocidad base sustentada",
                key="base_free_flow_speed_km_per_h",
                help="Ingrese la velocidad base sustentada por el estudio del proyecto.",
            )
        with right:
            no_passing = None
            driver_factor = None
            if multilane:
                driver_factor = st.selectbox(
                    "Factor de población de conductores, fP *",
                    ["Seleccione...", 1.0, 0.95, 0.90, 0.85],
                    format_func=lambda value: "Seleccione..." if value == "Seleccione..." else f"{value:.2f}",
                    key="driver_population_factor",
                    help="Valores documentados en el PDF de referencia; justifique la selección según el uso habitual/recreacional.",
                )
            else:
                no_passing = st.number_input(
                    "Zonas de no rebase (%) *", min_value=0.0, max_value=100.0,
                    value=None, step=1.0, key="no_passing_zones_percent",
                )
            field_notes = st.text_area(
                "Observaciones de campo (opcional)",
                placeholder="Anote condiciones cualitativas relevantes del levantamiento.",
                key="procedure_field_notes",
            )
    return {
        "field_notes": field_notes,
        "access_points_per_km": access_points,
        "no_passing_zones_percent": no_passing,
        "base_free_flow_speed_km_per_h": bffs,
        "driver_population_factor": None if driver_factor in (None, "Seleccione...") else float(driver_factor),
    }

