"""Capacity and oversaturation checks for two-lane highway segments."""

from dataclasses import dataclass

from calculations.exceptions import CalculationInputError


@dataclass(frozen=True)
class CapacityAssessment:
    """Capacity check for both equivalent flow computations."""

    volume_capacity_ratio: float
    highest_directional_flow_speed_pc_per_h: float
    highest_directional_flow_ptsf_pc_per_h: float
    oversaturated: bool


def assess_capacity(
    speed_flow_pc_per_h: float, ptsf_flow_pc_per_h: float,
    major_direction_fraction: float, two_way_capacity_pc_per_h: float,
    directional_capacity_pc_per_h: float,
) -> CapacityAssessment:
    """Check HCM 2000 Chapter 20 capacity limits and compute v/c.

    The HCM two-way worksheet uses the speed-analysis vp over 3,200 pc/h for
    v/c, and LOS F applies if either two-way or highest-direction demand
    exceeds the relevant 3,200/1,700 pc/h limit.
    """
    if not 0.5 <= major_direction_fraction <= 1:
        raise CalculationInputError("La proporción del sentido de mayor flujo debe estar entre 0.50 y 1.00.")
    if two_way_capacity_pc_per_h <= 0 or directional_capacity_pc_per_h <= 0:
        raise CalculationInputError("Las capacidades deben ser mayores que cero.")
    speed_direction = speed_flow_pc_per_h * major_direction_fraction
    ptsf_direction = ptsf_flow_pc_per_h * major_direction_fraction
    oversaturated = any((
        speed_flow_pc_per_h > two_way_capacity_pc_per_h,
        ptsf_flow_pc_per_h > two_way_capacity_pc_per_h,
        speed_direction > directional_capacity_pc_per_h,
        ptsf_direction > directional_capacity_pc_per_h,
    ))
    return CapacityAssessment(
        volume_capacity_ratio=speed_flow_pc_per_h / two_way_capacity_pc_per_h,
        highest_directional_flow_speed_pc_per_h=speed_direction,
        highest_directional_flow_ptsf_pc_per_h=ptsf_direction,
        oversaturated=oversaturated,
    )
