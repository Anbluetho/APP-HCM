"""Tests for TPDA/K3 and HCM Exhibit 20-12 demand disaggregation."""

import unittest

from calculations.design_hour_volume import calculate_design_hour_volume
from calculations.exceptions import CalculationInputError


class DesignHourVolumeTests(unittest.TestCase):
    def test_converts_using_major_direction_category(self) -> None:
        result = calculate_design_hour_volume(4000, 0.11, 60)

        self.assertAlmostEqual(result.vhd_two_way_veh_per_h, 440)
        self.assertAlmostEqual(result.vhd_analysis_direction_veh_per_h, 264)
        self.assertAlmostEqual(result.vhd_opposing_direction_veh_per_h, 176)
        self.assertEqual(result.analysis_direction_share_percent, 60)

    def test_specific_grade_can_use_opposing_share_from_same_category(self) -> None:
        result = calculate_design_hour_volume(
            4000, .11, 60, analysis_direction_is_major=False
        )
        self.assertAlmostEqual(result.vhd_analysis_direction_veh_per_h, 176)
        self.assertAlmostEqual(result.vhd_opposing_direction_veh_per_h, 264)

    def test_rejects_factor_outside_fraction_range(self) -> None:
        with self.assertRaises(CalculationInputError):
            calculate_design_hour_volume(4000, 1.1, 60)

    def test_rejects_category_not_available_in_exhibit_20_12(self) -> None:
        with self.assertRaises(CalculationInputError):
            calculate_design_hour_volume(4000, 0.11, 55)


if __name__ == "__main__":
    unittest.main()
