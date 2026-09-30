"""Equivalent passenger-car flow rate calculations for Chapter 20."""

from calculations.exceptions import CalculationInputError


def calculate_equivalent_flow_rate(
    hourly_volume_veh_per_h: float, peak_hour_factor: float,
    grade_adjustment_factor: float, heavy_vehicle_factor: float,
) -> float:
    """Calculate vp = V/(PHF*fG*fHV), HCM 2000 Chapter 20, Equation 20-3."""
    if hourly_volume_veh_per_h <= 0:
        raise CalculationInputError("El volumen horario debe ser mayor que cero.")
    if not 0 < peak_hour_factor <= 1:
        raise CalculationInputError("PHF debe estar en el intervalo (0, 1].")
    for name, value in (("fG", grade_adjustment_factor), ("fHV", heavy_vehicle_factor)):
        if not 0 < value <= 1:
            raise CalculationInputError(f"{name} debe estar en el intervalo (0, 1].")
    return hourly_volume_veh_per_h / (peak_hour_factor * grade_adjustment_factor * heavy_vehicle_factor)
