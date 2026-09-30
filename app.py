"""Streamlit entry point connecting the form to the independent HCM engine."""

import streamlit as st

from calculations.exceptions import CalculationError
from calculations.multilane_highway import analyze_multilane_segment
from calculations.two_lane_highway import analyze_two_way_segment
from data.data_loader import DataLoader
from data.procedure_verification import verify_multilane_tables, verify_two_lane_tables
from models.adapters import to_multilane_highway_inputs, to_two_lane_highway_inputs
from models.input_data import AnalysisInput
from models.validation import validate_analysis_input
from ui.results import (
    render_results,
    render_verification,
)
from ui.navigation import render_methodology, render_navigation
from ui.two_lane_highway import (
    render_facility_selection,
    render_geometric_inputs,
    render_operational_inputs,
    render_procedure_inputs,
    render_project_info,
    render_traffic_inputs,
)


st.set_page_config(
    page_title="Capacidad vial y LOS — HCM 2000",
    page_icon=":material/route:",
    layout="wide",
)
selected_view = render_navigation()
if selected_view == "Metodología":
    render_methodology()
    st.stop()

st.title("CAPACIDAD VIAL Y NIVEL DE SERVICIO")
st.subheader("Aplicación basada en procedimientos del HCM 2000")
st.caption("Herramienta académica para el análisis operacional de carreteras.")
with st.container(border=True):
    st.markdown(
        "**Flujo de trabajo**  \n"
        "1. Ingrese los datos del proyecto y del segmento.  "
        "2. Seleccione el procedimiento disponible.  "
        "3. Presione **CALCULAR** y revise resultados, verificación y advertencias."
    )

project = render_project_info()
facility = render_facility_selection()
geometry = render_geometric_inputs()
traffic = render_traffic_inputs()
operation = render_operational_inputs()
procedure_additional = render_procedure_inputs()

analysis_input: AnalysisInput = {
    "project": project,
    "facility": facility,
    "geometry": geometry,
    "traffic": traffic,
    "operation": operation,
    "procedure_additional": procedure_additional,
}

st.header("7. Cálculo")
calculate_clicked = st.button("CALCULAR", type="primary", key="calculate_analysis")
if calculate_clicked:
    # Keep the submitted snapshot even when validation fails, so the user can
    # see precisely which values were checked.
    st.session_state["hcm_submitted_inputs"] = analysis_input
    validation_errors = validate_analysis_input(analysis_input)
    st.session_state["hcm_validation_errors"] = validation_errors
    st.session_state["hcm_calculation_result"] = None
    st.session_state["hcm_table_checks"] = None
    st.session_state["hcm_lookup_succeeded"] = None
    st.session_state["hcm_calculation_errors"] = []

    if not validation_errors:
        multilane = facility["facility_type"] == "Carretera multicarril"
        if multilane:
            checks, all_tables_verified = verify_multilane_tables()
        else:
            checks, all_tables_verified = verify_two_lane_tables(DataLoader())
        st.session_state["hcm_table_checks"] = checks
        if not all_tables_verified:
            st.session_state["hcm_lookup_succeeded"] = False
            st.session_state["hcm_calculation_errors"] = [
                "No se ejecutó el motor porque una o más tablas requeridas no están disponibles o verificadas."
            ]
        else:
            try:
                if multilane:
                    calculation_inputs = to_multilane_highway_inputs(analysis_input)
                    result = analyze_multilane_segment(calculation_inputs)
                else:
                    calculation_inputs = to_two_lane_highway_inputs(analysis_input)
                    result = analyze_two_way_segment(calculation_inputs)
            except (CalculationError, ValueError) as exc:
                st.session_state["hcm_lookup_succeeded"] = False
                st.session_state["hcm_calculation_errors"] = [str(exc)]
            else:
                st.session_state["hcm_calculation_result"] = result
                st.session_state["hcm_lookup_succeeded"] = True

submitted_inputs = st.session_state.get("hcm_submitted_inputs")
calculation_result = st.session_state.get("hcm_calculation_result")
table_checks = st.session_state.get("hcm_table_checks")
lookup_succeeded = st.session_state.get("hcm_lookup_succeeded")
validation_errors = st.session_state.get("hcm_validation_errors", [])
calculation_errors = st.session_state.get("hcm_calculation_errors", [])

render_results(
    calculation_result,
    submitted_inputs,
    [*validation_errors, *calculation_errors],
)
render_verification(table_checks, lookup_succeeded=lookup_succeeded)
