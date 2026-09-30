"""Application navigation and static methodology overview."""

import streamlit as st

from reports.report_data import APPLICATION_VERSION


def render_navigation() -> str:
    """Render the sidebar navigation and return the selected application view."""
    with st.sidebar:
        st.title("Análisis vial")
        st.caption("Ingeniería civil · Capacidad y operación")
        selected_view = st.radio(
            "Navegación",
            ["Análisis", "Metodología"],
            key="application_view",
        )
        st.caption(f"Versión {APPLICATION_VERSION}")
    return selected_view


def render_methodology() -> None:
    """Explain the implemented procedures and the origin of their data."""
    st.title("Metodología y alcance")
    st.caption("Consulta rápida sobre los procedimientos conectados a la aplicación.")

    with st.container(border=True):
        st.subheader("Procedimientos disponibles")
        st.markdown(
            "- **Carretera de dos carriles:** HCM 2000, capítulo 20; análisis "
            "operacional de segmentos bidireccionales.\n"
            "- **Carretera multicarril:** transcripción académica secundaria de "
            "`C05-C07-Capacidad_2.pdf`; su procedencia se identifica en el informe."
        )
        st.warning(
            "El procedimiento multicarril debe cotejarse con el HCM 2000 original. "
            "No se incorporan parámetros propios de Ecuador."
        )

    with st.container(border=True):
        st.subheader("Trazabilidad de los datos")
        st.markdown(
            "- **Entradas del usuario:** demanda, geometría y condiciones del tramo.\n"
            "- **Tablas y factores metodológicos:** archivos de `data/hcm_tables/`, "
            "con metadatos y estado de verificación.\n"
            "- **Resultados calculados:** salidas del motor, presentadas en el "
            "informe junto con sus referencias.\n"
            "- **Responsable y origen de datos:** metadatos del análisis; no son "
            "variables matemáticas."
        )

    with st.container(border=True):
        st.subheader("Límites de uso")
        st.write(
            "Los datos no disponibles o no verificados detienen el cálculo. "
            "Revise la sección de verificación y las advertencias antes de usar "
            "los resultados en un análisis de ingeniería."
        )
