"""Performance measure equations for HCM 2000 two-way segments."""

from calculations.exceptions import CalculationInputError
from math import exp


def calculate_average_travel_speed(
    free_flow_speed_km_per_h: float, flow_pc_per_h: float,
    no_passing_adjustment_km_per_h: float,
) -> float:
    """Calculate ATS = FFS - 0.0125vp - fnp (HCM 2000, Equation 20-5)."""
    if free_flow_speed_km_per_h <= 0 or flow_pc_per_h < 0 or no_passing_adjustment_km_per_h < 0:
        raise CalculationInputError("FFS debe ser positiva; vp y fnp no pueden ser negativos.")
    return free_flow_speed_km_per_h - 0.0125 * flow_pc_per_h - no_passing_adjustment_km_per_h


def calculate_base_ptsf(flow_pc_per_h: float) -> float:
    """Calculate BPTSF=100(1-exp(-0.000879vp)), HCM 2000 Equation 20-7."""
    if flow_pc_per_h < 0:
        raise CalculationInputError("vp no puede ser negativo.")
    return 100.0 * (1.0 - exp(-0.000879 * flow_pc_per_h))


def calculate_ptsf(base_ptsf_percent: float, adjustment_percent: float) -> float:
    """Calculate PTSF = BPTSF + fd/np, HCM 2000 Equation 20-6."""
    if not 0 <= base_ptsf_percent <= 100 or adjustment_percent < 0:
        raise CalculationInputError("BPTSF debe estar entre 0–100% y el ajuste PTSF no puede ser negativo.")
    return base_ptsf_percent + adjustment_percent


def calculate_other_performance_measures(
    hourly_volume_veh_per_h: float, peak_hour_factor: float,
    segment_length_km: float, average_travel_speed_km_per_h: float,
) -> dict[str, float]:
    """Compute worksheet travel totals from the HCM 2000 Chapter 20 example.

    Returns peak 15-min vehicle-km, peak-hour vehicle-km, and peak 15-min
    total travel time. These are worksheet performance measures, not LOS inputs.
    """
    if hourly_volume_veh_per_h < 0 or segment_length_km <= 0:
        raise CalculationInputError("Volumen no negativo y longitud mayor que cero requeridos.")
    if not 0 < peak_hour_factor <= 1 or average_travel_speed_km_per_h <= 0:
        raise CalculationInputError("PHF debe estar en (0,1] y ATS debe ser positiva.")
    vkm_15 = 0.25 * segment_length_km * hourly_volume_veh_per_h / peak_hour_factor
    vkm_60 = hourly_volume_veh_per_h * segment_length_km
    return {
        "vehicle_km_peak_15_min": vkm_15,
        "vehicle_km_peak_hour": vkm_60,
        "travel_time_peak_15_min_veh_h": vkm_15 / average_travel_speed_km_per_h,
    }
