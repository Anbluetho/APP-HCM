"""Streamlit integration checks for the compact two-lane workflow."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class TwoLaneStreamlitTests(unittest.TestCase):
    def test_form_preserves_two_lane_hcm_workflow(self) -> None:
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.text_input(key="project_name").set_value("Prueba dos carriles")
        app.text_input(key="project_location").set_value("Tramo de prueba")
        for key, value in {
            "segment_length_km": 10.0,
            "lane_width_m": 3.4,
            "shoulder_width_m": 1.2,
            "design_demand_tpda": 16000.0,
            "design_demand_k3": 0.10,
            "peak_hour_factor": 0.95,
            "trucks_percent": 14.0,
            "recreational_vehicles_percent": 4.0,
            "access_points_per_km": 12.0,
            "base_free_flow_speed_km_per_h": 100.0,
            "no_passing_zones_percent": 50.0,
        }.items():
            app.number_input(key=key).set_value(value)
        app.selectbox(key="hcm_major_direction_split").set_value(50)
        app.selectbox(key="terrain").set_value("ondulado")
        app.selectbox(key="highway_class").set_value("I")
        self.assertFalse(any(widget.key == "design_demand_direction_share" for widget in app.number_input))
        app.button(key="calculate_analysis").click().run()

        self.assertEqual(len(app.exception), 0)
        result = app.session_state["hcm_calculation_result"]
        self.assertEqual(result.final_results["level_of_service"], "E")

    def test_form_starts_with_only_the_supported_two_lane_facility(self) -> None:
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(any(widget.key == "facility_type" for widget in app.selectbox))
        self.assertEqual(len(app.button), 1)
        self.assertTrue(any("Carretera de dos carriles" in item.value for item in app.markdown))

    def test_specific_grade_form_routes_to_directional_engine(self) -> None:
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30
        ).run()
        app.radio(key="analysis_type").set_value("Pendiente específica").run()
        values = {
            "specific_grade_percent": 3.2,
            "specific_grade_length_km": 1.2,
            "design_demand_tpda": 1000.0,
            "design_demand_k3": 0.9,
            "specific_grade_phf": 0.95,
            "specific_grade_analysis_trucks": 10.0,
            "specific_grade_analysis_rvs": 2.0,
            "specific_grade_opposing_trucks": 8.0,
            "specific_grade_opposing_rvs": 1.0,
            "specific_grade_no_passing_percent": 50.0,
            "specific_grade_lane_width": 3.3,
            "specific_grade_shoulder_width": 1.2,
            "specific_grade_access_points": 6.0,
            "specific_grade_bffs_analysis": 100.0,
        }
        for key, value in values.items():
            app.number_input(key=key).set_value(value)
        app.selectbox(key="hcm_major_direction_split").set_value(60)
        app.selectbox(key="specific_grade_highway_class").set_value("I")
        app.radio(key="specific_grade_flow_role").set_value("Mayor flujo")
        app.selectbox(key="specific_grade_crawl_condition").set_value("No")
        app.button(key="calculate_analysis").click().run()

        self.assertEqual(len(app.exception), 0)
        result = app.session_state["hcm_specific_grade_result"]
        self.assertIn(result.final_results["level_of_service"], "ABCDEF")
        self.assertEqual(result.final_results["capacity_pc_per_h_direction"], 1700.0)
        self.assertAlmostEqual(result.inputs["analysis_volume_veh_per_h"], 540.0)
        self.assertAlmostEqual(result.inputs["opposing_volume_veh_per_h"], 360.0)
        self.assertNotIn("direction_share_percent", result.inputs)

    def test_specific_grade_form_explains_missing_crawl_inputs(self) -> None:
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30
        ).run()
        app.radio(key="analysis_type").set_value("Pendiente específica").run()
        values = {
            "specific_grade_percent": 3.2,
            "specific_grade_length_km": 1.2,
            "design_demand_tpda": 1000.0,
            "design_demand_k3": 0.9,
            "specific_grade_phf": 0.95,
            "specific_grade_analysis_trucks": 10.0,
            "specific_grade_analysis_rvs": 2.0,
            "specific_grade_opposing_trucks": 8.0,
            "specific_grade_opposing_rvs": 1.0,
            "specific_grade_no_passing_percent": 50.0,
            "specific_grade_lane_width": 3.3,
            "specific_grade_shoulder_width": 1.2,
            "specific_grade_access_points": 6.0,
            "specific_grade_bffs_analysis": 100.0,
        }
        for key, value in values.items():
            app.number_input(key=key).set_value(value)
        app.selectbox(key="hcm_major_direction_split").set_value(60)
        app.selectbox(key="specific_grade_highway_class").set_value("I")
        app.radio(key="specific_grade_flow_role").set_value("Mayor flujo")
        app.selectbox(key="specific_grade_crawl_condition").set_value("Sí")
        app.button(key="calculate_analysis").click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("proporción de camiones" in error.value for error in app.error))


if __name__ == "__main__":
    unittest.main()
