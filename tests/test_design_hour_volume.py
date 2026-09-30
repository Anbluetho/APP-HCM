"""Tests for the local TPDA/K3/D conversion that precedes HCM analysis."""

import unittest

from calculations.design_hour_volume import calculate_design_hour_volume
from calculations.exceptions import CalculationInputError


class DesignHourVolumeTests(unittest.TestCase):
    def test_converts_tpda_to_two_way_and_directional_design_hour_volumes(self) -> None:
        result = calculate_design_hour_volume(4000, 0.11, 60)

        self.assertAlmostEqual(result.vhd_two_way_veh_per_h, 440)
        self.assertAlmostEqual(result.vhd_analysis_direction_veh_per_h, 264)
        self.assertAlmostEqual(result.vhd_opposing_direction_veh_per_h, 176)

    def test_rejects_factor_outside_fraction_range(self) -> None:
        with self.assertRaises(CalculationInputError):
            calculate_design_hour_volume(4000, 1.1, 60)

    def test_rejects_direction_share_outside_percent_range(self) -> None:
        with self.assertRaises(CalculationInputError):
            calculate_design_hour_volume(4000, 0.11, 101)


if __name__ == "__main__":
    unittest.main()
