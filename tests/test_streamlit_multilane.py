"""Streamlit integration check for the multilane user workflow."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class MultilaneStreamlitTests(unittest.TestCase):
    def test_form_preserves_two_lane_hcm_workflow(self) -> None:
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.text_input(key="project_name").set_value("Prueba dos carriles")
        app.text_input(key="project_location").set_value("Tramo de prueba")
        for key, value in {
            "segment_length_km": 10.0,
            "lane_width_m": 3.4,
            "shoulder_width_m": 1.2,
            "hourly_volume_two_way": 1600.0,
            "peak_hour_factor": 0.95,
            "trucks_percent": 14.0,
            "recreational_vehicles_percent": 4.0,
            "access_points_per_km": 12.0,
            "base_free_flow_speed_km_per_h": 100.0,
            "no_passing_zones_percent": 50.0,
        }.items():
            app.number_input(key=key).set_value(value)
        app.selectbox(key="major_direction_split").set_value(50)
        app.selectbox(key="terrain").set_value("ondulado")
        app.selectbox(key="highway_class").set_value("I")
        app.button(key="calculate_analysis").click().run()

        self.assertEqual(len(app.exception), 0)
        result = app.session_state["hcm_calculation_result"]
        self.assertEqual(result.final_results["level_of_service"], "E")

    def test_form_runs_multilane_example_and_renders_results(self) -> None:
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
        app.text_input(key="project_name").set_value("Prueba multicarril")
        app.text_input(key="project_location").set_value("Tramo de prueba")
        app.selectbox(key="facility_type").set_value("Carretera multicarril")
        app.run()

        for key, value in {
            "lane_width_m": 3.5,
            "lateral_clearance_m": 1.8,
            "hourly_volume_two_way": 3600.0,
            "peak_hour_factor": 0.92,
            "trucks_percent": 8.0,
            "recreational_vehicles_percent": 0.0,
            "access_points_per_km": 12.0,
            "base_free_flow_speed_km_per_h": 100.0,
        }.items():
            app.number_input(key=key).set_value(value)
        app.selectbox(key="lanes_per_direction").set_value(2)
        app.selectbox(key="major_direction_split").set_value(50)
        app.selectbox(key="terrain").set_value("ondulado")
        app.selectbox(key="median_type").set_value("divided")
        app.selectbox(key="driver_population_factor").set_value(1.0)
        app.button(key="calculate_analysis").click().run()

        self.assertEqual(len(app.exception), 0)
        result = app.session_state["hcm_calculation_result"]
        self.assertIsNotNone(result)
        self.assertEqual(result.final_results["level_of_service"], "C")
        self.assertTrue(any(metric.label == "Clasificación LOS" for metric in app.metric))


if __name__ == "__main__":
    unittest.main()
