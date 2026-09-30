"""Unit and worked-example tests for the HCM 2000 calculation functions."""

import unittest

from calculations.capacity import assess_capacity
from calculations.exceptions import CalculationInputError
from calculations.flow import calculate_equivalent_flow_rate
from calculations.heavy_vehicles import calculate_heavy_vehicle_factor
from calculations.los import classify_level_of_service
from calculations.performance import (
    calculate_average_travel_speed,
    calculate_base_ptsf,
    calculate_other_performance_measures,
    calculate_ptsf,
)
from calculations.phf import calculate_phf
from calculations.two_lane_highway import analyze_two_way_segment
from data.data_loader import DataLoader
from models.two_lane_highway import TwoLaneHighwayInputs


class HcmCalculationTests(unittest.TestCase):
    """Verify individual equations, validation, and HCM Example Problem 1."""

    def test_peak_hour_factor(self) -> None:
        self.assertAlmostEqual(calculate_phf(1600, 1600 / (4 * 0.95)), 0.95)
        with self.assertRaises(CalculationInputError):
            calculate_phf(100, 0)

    def test_heavy_vehicle_factor(self) -> None:
        result = calculate_heavy_vehicle_factor(14, 4, 1.5, 1.1)
        self.assertAlmostEqual(result, 0.931, places=3)
        with self.assertRaises(CalculationInputError):
            calculate_heavy_vehicle_factor(80, 30, 1.5, 1.1)

    def test_equivalent_flow_rate(self) -> None:
        result = calculate_equivalent_flow_rate(1600, 0.95, 0.99, 0.931)
        self.assertAlmostEqual(result, 1827, delta=1)
        with self.assertRaises(CalculationInputError):
            calculate_equivalent_flow_rate(1600, 1.1, 1, 1)

    def test_capacity_thresholds(self) -> None:
        under = assess_capacity(1827, 1684, 0.5, 3200, 1700)
        self.assertFalse(under.oversaturated)
        self.assertAlmostEqual(under.volume_capacity_ratio, 1827 / 3200)
        over = assess_capacity(3401, 3300, 0.6, 3200, 1700)
        self.assertTrue(over.oversaturated)

    def test_performance_measures(self) -> None:
        self.assertAlmostEqual(calculate_average_travel_speed(89.2, 1827, 1.3), 65.0625)
        bptsf = calculate_base_ptsf(1684)
        self.assertAlmostEqual(bptsf, 77.2, places=1)
        self.assertAlmostEqual(calculate_ptsf(bptsf, 4.8), 82.0, places=1)
        other = calculate_other_performance_measures(1600, 0.95, 10, 65.1)
        self.assertAlmostEqual(other["vehicle_km_peak_15_min"], 4211, delta=1)
        self.assertAlmostEqual(other["vehicle_km_peak_hour"], 16000)
        self.assertAlmostEqual(other["travel_time_peak_15_min_veh_h"], 64.7, places=1)

    def test_los_from_verified_exhibits(self) -> None:
        records = DataLoader().load_table("los_carreteras_dos_carriles")
        self.assertEqual(classify_level_of_service("I", 82, 65.1, records), "E")
        self.assertEqual(classify_level_of_service("II", 75.2, None, records), "D")

    def test_hcm_2000_example_problem_1(self) -> None:
        """HCM 2000 Chapter 20, Example Problem 1, printed pp. 20-33–20-34."""
        inputs = TwoLaneHighwayInputs(
            hourly_volume_veh_per_h=1600,
            peak_hour_factor=0.95,
            major_direction_percent=50,
            trucks_percent=14,
            recreational_vehicles_percent=4,
            terrain="rolling",
            highway_class="I",
            segment_length_km=10,
            lane_width_m=3.4,
            shoulder_width_m=1.2,
            access_points_per_km=12,
            no_passing_zones_percent=50,
            base_free_flow_speed_km_per_h=100,
        )
        result = analyze_two_way_segment(inputs)
        self.assertAlmostEqual(result.parameters["free_flow_speed_adjustment_lane_shoulder_km_per_h"], 2.8)
        self.assertAlmostEqual(result.parameters["free_flow_speed_adjustment_access_km_per_h"], 8.0)
        self.assertAlmostEqual(result.intermediate_results["free_flow_speed_km_per_h"], 89.2)
        self.assertAlmostEqual(result.intermediate_results["speed_vp_pc_per_h"], 1827, delta=1)
        self.assertAlmostEqual(result.intermediate_results["ptsf_vp_pc_per_h"], 1684, delta=1)
        self.assertAlmostEqual(result.intermediate_results["fnp_adjustment_km_per_h"], 1.3, places=1)
        self.assertAlmostEqual(result.final_results["average_travel_speed_km_per_h"], 65.1, places=0)
        self.assertAlmostEqual(result.final_results["percent_time_spent_following"], 82.0, places=0)
        self.assertAlmostEqual(result.final_results["volume_capacity_ratio"], 0.57, places=2)
        self.assertEqual(result.final_results["level_of_service"], "E")
        self.assertIn("speed_vp_pc_per_h", result.intermediate_results)
        self.assertTrue(result.formula_references)

    def test_hcm_2000_example_problem_2(self) -> None:
        """HCM 2000 Chapter 20, Example Problem 2, printed pp. 20-36–20-37."""
        inputs = TwoLaneHighwayInputs(
            hourly_volume_veh_per_h=1050, peak_hour_factor=0.85,
            major_direction_percent=70, trucks_percent=5,
            recreational_vehicles_percent=7, terrain="rolling",
            highway_class="II", segment_length_km=10, lane_width_m=3.0,
            shoulder_width_m=0.6, access_points_per_km=6,
            no_passing_zones_percent=60, base_free_flow_speed_km_per_h=90,
        )
        result = analyze_two_way_segment(inputs)
        self.assertAlmostEqual(result.intermediate_results["speed_vp_pc_per_h"], 1288, delta=1)
        self.assertAlmostEqual(result.intermediate_results["ptsf_vp_pc_per_h"], 1235, delta=1)
        self.assertAlmostEqual(result.final_results["average_travel_speed_km_per_h"], 61.7, places=0)
        self.assertAlmostEqual(result.final_results["percent_time_spent_following"], 75.2, places=0)
        self.assertEqual(result.final_results["level_of_service"], "D")

    def test_analyzer_rejects_unrepresented_table_inputs(self) -> None:
        inputs = TwoLaneHighwayInputs(
            1600, .95, 55, 14, 4, "rolling", "I", 10, 3.4, 1.2, 12, 50, 100,
        )
        with self.assertRaisesRegex(CalculationInputError, "tabla 20-12"):
            analyze_two_way_segment(inputs)

    def test_level_terrain_uses_table_terminology_per_exhibit(self) -> None:
        base = TwoLaneHighwayInputs(
            1600, .95, 50, 14, 4, "level", "I", 10, 3.4, 1.2,
            12, 50, 100,
        )
        result = analyze_two_way_segment(base)
        self.assertEqual(result.parameters["grade_adjustment_ptsf"], 1.0)


if __name__ == "__main__":
    unittest.main()
