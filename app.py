"""Streamlit entry point for the HCM 2000 two-lane highway calculator."""

import streamlit as st

from calculations.exceptions import CalculationError
from calculations.specific_grade import analyze_specific_grade
from calculations.specific_grade.analyzer import (
    SpecificGradeAnalyzer,
    verify_specific_grade_tables,
)
from calculations.two_lane_highway import analyze_two_way_segment
from data.data_loader import DataLoader
from data.procedure_verification import (
    verify_two_lane_tables,
)
from models.adapters import to_two_lane_highway_inputs
from models.input_data import AnalysisInput
from models.validation import validate_analysis_input
from ui.results import render_results, render_specific_grade_results
from ui.two_lane_highway import (
    render_analysis_type,
    render_facility_selection,
    render_geometric_inputs,
    render_operational_inputs,
    render_procedure_inputs,
    render_project_info,
    render_specific_grade_inputs,
    render_traffic_inputs,
)


st.set_page_config(
    page_title="HCM 2000 — Carreteras de dos carriles",
    page_icon=":material/route:",
    layout="centered",
)

st.title("HCM 2000 — Carreteras de dos carriles")
st.caption(
    "Calculadora académica de capacidad y nivel de servicio para segmentos "
    "bidireccionales. El cálculo utiliza las tablas HCM documentadas en el proyecto."
)

project = render_project_info()
facility = render_facility_selection()
analysis_type = render_analysis_type()

if analysis_type == "Segmento bidireccional extendido":
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
    calculate_clicked = st.button(
        "CALCULAR NIVEL DE SERVICIO", type="primary", key="calculate_analysis"
    )
    if calculate_clicked:
        st.session_state["hcm_last_analysis_type"] = "general"
        st.session_state["hcm_submitted_inputs"] = analysis_input
        validation_errors = validate_analysis_input(analysis_input)
        st.session_state["hcm_validation_errors"] = validation_errors
        st.session_state["hcm_calculation_result"] = None
        st.session_state["hcm_specific_grade_result"] = None
        st.session_state["hcm_table_checks"] = None
        st.session_state["hcm_lookup_succeeded"] = None
        st.session_state["hcm_calculation_errors"] = []

        if not validation_errors:
            checks, all_tables_verified = verify_two_lane_tables(DataLoader())
            st.session_state["hcm_table_checks"] = checks
            if not all_tables_verified:
                st.session_state["hcm_lookup_succeeded"] = False
                st.session_state["hcm_calculation_errors"] = [
                    "No se ejecutó el motor porque una o más tablas requeridas "
                    "no están disponibles o verificadas."
                ]
            else:
                try:
                    calculation_inputs = to_two_lane_highway_inputs(analysis_input)
                    result = analyze_two_way_segment(calculation_inputs)
                except (CalculationError, ValueError) as exc:
                    st.session_state["hcm_lookup_succeeded"] = False
                    st.session_state["hcm_calculation_errors"] = [str(exc)]
                else:
                    st.session_state["hcm_calculation_result"] = result
                    st.session_state["hcm_lookup_succeeded"] = True

    if st.session_state.get("hcm_last_analysis_type") in {None, "general"}:
        render_results(
            st.session_state.get("hcm_calculation_result"),
            st.session_state.get("hcm_submitted_inputs"),
            [
                *st.session_state.get("hcm_validation_errors", []),
                *st.session_state.get("hcm_calculation_errors", []),
            ],
            table_checks=st.session_state.get("hcm_table_checks"),
            lookup_succeeded=st.session_state.get("hcm_lookup_succeeded"),
        )
else:
    specific_inputs = render_specific_grade_inputs()
    calculate_clicked = st.button(
        "CALCULAR NIVEL DE SERVICIO", type="primary", key="calculate_analysis"
    )
    if calculate_clicked:
        st.session_state["hcm_last_analysis_type"] = "specific_grade"
        st.session_state["hcm_specific_grade_result"] = None
        st.session_state["hcm_calculation_result"] = None
        st.session_state["hcm_table_checks"] = None
        st.session_state["hcm_lookup_succeeded"] = None
        st.session_state["hcm_calculation_errors"] = []
        st.session_state["hcm_validation_errors"] = []
        try:
            SpecificGradeAnalyzer.validate_inputs(specific_inputs)
        except (CalculationError, ValueError) as exc:
            st.session_state["hcm_calculation_errors"] = [str(exc)]
        else:
            checks, all_tables_verified = verify_specific_grade_tables(DataLoader())
            st.session_state["hcm_table_checks"] = checks
            if not all_tables_verified:
                st.session_state["hcm_lookup_succeeded"] = False
                st.session_state["hcm_calculation_errors"] = [
                    "No se ejecutó el motor porque una o más tablas del procedimiento "
                    "de pendiente específica no están disponibles o verificadas."
                ]
            else:
                try:
                    result = analyze_specific_grade(specific_inputs)
                except (CalculationError, ValueError) as exc:
                    st.session_state["hcm_lookup_succeeded"] = False
                    st.session_state["hcm_calculation_errors"] = [str(exc)]
                else:
                    st.session_state["hcm_specific_grade_result"] = result
                    st.session_state["hcm_lookup_succeeded"] = True

    if st.session_state.get("hcm_last_analysis_type") in {None, "specific_grade"}:
        render_specific_grade_results(
            st.session_state.get("hcm_specific_grade_result"),
            [
                *st.session_state.get("hcm_validation_errors", []),
                *st.session_state.get("hcm_calculation_errors", []),
            ],
            table_checks=st.session_state.get("hcm_table_checks"),
            lookup_succeeded=st.session_state.get("hcm_lookup_succeeded"),
        )
