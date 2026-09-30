"""Regression check against the supplied multilane worked example."""

import unittest

from calculations.multilane_highway import analyze_multilane_segment
from models.multilane_highway import MultilaneHighwayInputs


class MultilaneCalculationTests(unittest.TestCase):
    def test_puce_worked_example(self) -> None:
        """Reproduce the document's directional demand and reported LOS C."""
        inputs = MultilaneHighwayInputs(
            hourly_volume_two_way_veh_per_h=3600,
            peak_hour_factor=0.92,
            major_direction_percent=50,
            trucks_percent=8,
            recreational_vehicles_percent=0,
            terrain="ondulado",
            lanes_per_direction=2,
            lane_width_m=3.5,
            lateral_clearance_m=1.8,
            median_type="divided",
            access_points_per_km=12,
            base_free_flow_speed_km_per_h=100,
            driver_population_factor=1.0,
        )
        result = analyze_multilane_segment(inputs)
        self.assertAlmostEqual(result.intermediate_results["free_flow_speed_km_per_h"], 88.9)
        self.assertAlmostEqual(result.intermediate_results["adjusted_flow_pc_per_h_per_lane"], 1095.65, places=1)
        self.assertAlmostEqual(result.intermediate_results["operating_speed_km_per_h"], 88.9)
        self.assertAlmostEqual(result.intermediate_results["density_pc_per_km_per_lane"], 12.3, places=1)
        self.assertEqual(result.final_results["level_of_service"], "C")

    def test_escarpado_stops_for_missing_documented_factors(self) -> None:
        inputs = MultilaneHighwayInputs(
            hourly_volume_two_way_veh_per_h=1000,
            peak_hour_factor=0.9,
            major_direction_percent=50,
            trucks_percent=0,
            recreational_vehicles_percent=0,
            terrain="escarpado",
            lanes_per_direction=2,
            lane_width_m=3.5,
            lateral_clearance_m=1.8,
            median_type="divided",
            access_points_per_km=12,
            base_free_flow_speed_km_per_h=100,
            driver_population_factor=1.0,
        )
        with self.assertRaisesRegex(ValueError, "no contiene equivalencias"):
            analyze_multilane_segment(inputs)


if __name__ == "__main__":
    unittest.main()
