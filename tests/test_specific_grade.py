"""Tests for HCM 2000 specific-grade tables and directional calculations."""

import unittest

from calculations.exceptions import CalculationDataError, CalculationInputError
from calculations.specific_grade.analyzer import SpecificGradeAnalyzer
from calculations.specific_grade.flow import (
    calculate_crawl_heavy_vehicle_factor,
    calculate_directional_flow,
    lookup_upgrade_value,
)
from calculations.specific_grade.performance import (
    calculate_directional_ats,
    calculate_directional_base_ptsf,
    calculate_directional_ptsf,
    interpolate_directional_no_passing_adjustment,
    lookup_ptsf_coefficients,
)
from data.data_loader import DataLoader
from data.procedure_verification import verify_specific_grade_tables
from models.specific_grade import SpecificGradeInputs


class SpecificGradeCalculationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loader = DataLoader()
        cls.tables = {
            "exhibit_20_13": cls.loader.load_table("specific_grade_20_13_ats_fg"),
            "exhibit_20_14": cls.loader.load_table("specific_grade_20_14_ptsf_fg"),
            "exhibit_20_15": cls.loader.load_table("specific_grade_20_15_ats_et"),
            "exhibit_20_16": cls.loader.load_table("specific_grade_20_16_ptsf_et_er"),
            "exhibit_20_17": cls.loader.load_table("specific_grade_20_17_ats_er"),
            "exhibit_20_18": cls.loader.load_table("specific_grade_20_18_crawl_etc"),
            "exhibit_20_19": cls.loader.load_table("specific_grade_20_19_ats_fnp"),
            "exhibit_20_20": cls.loader.load_table("specific_grade_20_20_ptsf_fnp"),
            "exhibit_20_21": cls.loader.load_table("specific_grade_20_21_ptsf_coefficients"),
            "specific_downgrade_fG": cls.loader.load_table("specific_downgrade_fg_reference"),
            "tabla_20_9_equivalentes_velocidad": cls.loader.load_table("tabla_20_9_equivalentes_velocidad"),
            "tabla_20_10_equivalentes_ptsf": cls.loader.load_table("tabla_20_10_equivalentes_ptsf"),
        }

    @staticmethod
    def inputs(**changes: object) -> SpecificGradeInputs:
        values: dict[str, object] = {
            "analysis_grade_direction": "upgrade",
            "grade_percent": 3.2,
            "grade_length_km": 1.2,
            "analysis_volume_veh_per_h": 600.0,
            "opposing_volume_veh_per_h": 300.0,
            "peak_hour_factor": 0.95,
            "analysis_trucks_percent": 10.0,
            "analysis_rvs_percent": 2.0,
            "opposing_trucks_percent": 8.0,
            "opposing_rvs_percent": 1.0,
            "highway_class": "I",
            "lane_width_m": 3.3,
            "shoulder_width_m": 1.2,
            "access_points_per_km": 6.0,
            "no_passing_zones_percent": 50.0,
            "base_free_flow_speed_analysis_km_per_h": 100.0,
            "downhill_crawl_condition": False,
        }
        values.update(changes)
        return SpecificGradeInputs(**values)  # type: ignore[arg-type]

    def test_source_tables_are_registered_and_loadable(self) -> None:
        checks, verified = verify_specific_grade_tables(self.loader)
        self.assertTrue(verified)
        self.assertEqual(len(checks), 16)
        self.assertTrue(all(row["Estado"] == "Disponible y verificada" for row in checks))

    def test_upgrade_lookup_uses_hcm_grade_length_and_flow_band(self) -> None:
        self.assertAlmostEqual(
            lookup_upgrade_value(self.tables["exhibit_20_13"], 3.2, 3.2, "0-300", "fG"),
            0.75,
        )
        self.assertAlmostEqual(
            lookup_upgrade_value(self.tables["exhibit_20_15"], 3.2, 1.2, "0-300", "ET"),
            4.5,
        )

    def test_upgrade_length_interpolation_is_bounded_to_table(self) -> None:
        rows = self.tables["exhibit_20_13"]
        value = lookup_upgrade_value(rows, 3.2, 2.0, "0-300", "fG")
        self.assertAlmostEqual(value, 0.755)
        with self.assertRaises(CalculationInputError):
            lookup_upgrade_value(rows, 3.2, 0.39, "0-300", "fG")

    def test_hcm_example_3_directional_equations_and_exhibits_20_19_to_21(self) -> None:
        # HCM 2000 Chapter 20, Example Problem 3 (directional segment checks).
        ats_fnp = interpolate_directional_no_passing_adjustment(
            self.tables["exhibit_20_19"], free_flow_speed_km_per_h=89.2,
            opposing_flow_pc_per_h=512.0, no_passing_zones_percent=50.0,
            value_field="fnp_kmh",
        )
        ptsf_fnp = interpolate_directional_no_passing_adjustment(
            self.tables["exhibit_20_20"], free_flow_speed_km_per_h=89.2,
            opposing_flow_pc_per_h=479.0, no_passing_zones_percent=50.0,
            value_field="fnp_ptsf_pct",
        )
        a, b = lookup_ptsf_coefficients(self.tables["exhibit_20_21"], 479.0)
        ats = calculate_directional_ats(89.2, 1370.0, 512.0, ats_fnp)
        base_ptsf = calculate_directional_base_ptsf(1263.0, a, b)
        ptsf = calculate_directional_ptsf(base_ptsf, ptsf_fnp)
        self.assertAlmostEqual(ats_fnp, 2.7, places=1)
        self.assertAlmostEqual(ptsf_fnp, 11.7, places=1)
        self.assertAlmostEqual(a, -0.074, places=3)
        self.assertAlmostEqual(b, 0.453, places=3)
        self.assertAlmostEqual(ats, 63.0, places=0)
        self.assertAlmostEqual(base_ptsf, 84.7, places=0)
        self.assertAlmostEqual(ptsf, 96.4, places=0)

    def test_zero_no_passing_zones_produces_zero_adjustment(self) -> None:
        adjustment = interpolate_directional_no_passing_adjustment(
            self.tables["exhibit_20_19"], free_flow_speed_km_per_h=90.0,
            opposing_flow_pc_per_h=400.0, no_passing_zones_percent=0.0,
            value_field="fnp_kmh",
        )
        self.assertEqual(adjustment, 0.0)

    def test_iteration_updates_flow_band_until_stable(self) -> None:
        result = calculate_directional_flow(
            volume_veh_per_h=250.0, peak_hour_factor=1.0,
            grade_direction="upgrade", grade_percent=3.2,
            grade_length_km=1.2, purpose="ats", trucks_percent=40.0,
            rvs_percent=0.0, tables=self.tables,
        )
        self.assertGreaterEqual(len(result.iterations), 2)
        self.assertEqual(result.iterations[0].selected_flow_band, "0-300")
        self.assertEqual(result.flow_band, ">300-600")
        self.assertEqual(result.iterations[-1].selected_flow_band, result.flow_band)

    def test_crawl_heavy_vehicle_factor_uses_equation_20_14(self) -> None:
        fhv = calculate_crawl_heavy_vehicle_factor(
            trucks_percent=20.0,
            trucks_at_crawl_percent=50.0,
            rvs_percent=5.0,
            truck_equivalency=2.0,
            rv_equivalency=1.2,
            crawl_truck_equivalency=10.0,
        )
        expected = 1.0 / (1 + 0.5 * 0.2 * 9 + 0.5 * 0.2 * 1 + 0.05 * 0.2)
        self.assertAlmostEqual(fhv, expected)

    def test_specific_grade_applicability_boundaries(self) -> None:
        with self.assertRaisesRegex(CalculationInputError, "al menos 3 %"):
            SpecificGradeAnalyzer.validate_inputs(self.inputs(grade_percent=2.9))
        SpecificGradeAnalyzer.validate_inputs(
            self.inputs(grade_percent=3.0, grade_length_km=0.4)
        )
        SpecificGradeAnalyzer.validate_inputs(
            self.inputs(grade_percent=3.2, grade_length_km=1.0)
        )
        SpecificGradeAnalyzer.validate_inputs(
            self.inputs(grade_percent=3.2, grade_length_km=0.4)
        )
        with self.assertRaisesRegex(CalculationInputError, "1,0 km"):
            SpecificGradeAnalyzer.validate_inputs(
                self.inputs(analysis_grade_direction="downgrade", grade_length_km=0.9)
            )

    def test_crawl_case_requires_all_source_inputs(self) -> None:
        with self.assertRaisesRegex(CalculationInputError, "proporción de camiones"):
            SpecificGradeAnalyzer.validate_inputs(
                self.inputs(downhill_crawl_condition=True)
            )
        with self.assertRaisesRegex(CalculationInputError, "BFFS del sentido descendente"):
            SpecificGradeAnalyzer.validate_inputs(
                self.inputs(
                    downhill_crawl_condition=True,
                    downhill_trucks_at_crawl_percent=50.0,
                    downhill_truck_crawl_speed_km_per_h=40.0,
                )
            )

    def test_directional_capacity_is_1700_and_equal_capacity_is_los_f(self) -> None:
        result = SpecificGradeAnalyzer(self.loader).analyze(
            self.inputs(
                analysis_grade_direction="downgrade",
                grade_percent=3.0,
                grade_length_km=1.0,
                analysis_volume_veh_per_h=1700.0,
                opposing_volume_veh_per_h=0.0,
                peak_hour_factor=1.0,
                analysis_trucks_percent=0.0,
                analysis_rvs_percent=0.0,
                opposing_trucks_percent=0.0,
                opposing_rvs_percent=0.0,
                no_passing_zones_percent=20.0,
            )
        )
        self.assertEqual(result.final_results["capacity_pc_per_h_direction"], 1700.0)
        self.assertEqual(result.final_results["volume_capacity_ratio"], 1.0)
        self.assertEqual(result.final_results["level_of_service"], "F")
        self.assertIsNone(result.final_results["average_travel_speed_km_per_h"])

    def test_flow_just_below_directional_capacity_is_still_calculated(self) -> None:
        result = SpecificGradeAnalyzer(self.loader).analyze(
            self.inputs(
                analysis_grade_direction="downgrade",
                grade_percent=3.0,
                grade_length_km=1.0,
                analysis_volume_veh_per_h=1699.9,
                opposing_volume_veh_per_h=0.0,
                peak_hour_factor=1.0,
                analysis_trucks_percent=0.0,
                analysis_rvs_percent=0.0,
                opposing_trucks_percent=0.0,
                opposing_rvs_percent=0.0,
                no_passing_zones_percent=0.0,
            )
        )
        self.assertLess(result.final_results["volume_capacity_ratio"], 1.0)
        self.assertIsNotNone(result.final_results["average_travel_speed_km_per_h"])

    def test_specific_downgrade_crawl_condition_uses_crawl_table(self) -> None:
        result = SpecificGradeAnalyzer(self.loader).analyze(
            self.inputs(
                analysis_grade_direction="downgrade",
                downhill_crawl_condition=True,
                downhill_trucks_at_crawl_percent=50.0,
                downhill_truck_crawl_speed_km_per_h=40.0,
            )
        )
        self.assertIn("crawl_truck_equivalency_ats_analysis", result.parameters)
        self.assertIn("crawl_equation_source", result.parameters)

    def test_end_to_end_upgrade_and_downgrade(self) -> None:
        for grade_direction, length in (("upgrade", 0.4), ("downgrade", 1.0)):
            result = SpecificGradeAnalyzer(self.loader).analyze(
                self.inputs(
                    analysis_grade_direction=grade_direction,
                    grade_length_km=length,
                )
            )
            self.assertIn(result.final_results["level_of_service"], "ABCDEF")
            self.assertGreaterEqual(result.final_results["volume_capacity_ratio"], 0)
            self.assertIn("ats_analysis", result.intermediate_results["flow_iterations"])


if __name__ == "__main__":
    unittest.main()
