"""Peak-hour-factor calculation for the HCM 2000 two-lane procedure."""

from calculations.exceptions import CalculationInputError


def calculate_phf(hourly_volume_veh_per_h: float, peak_15_min_volume_veh: float) -> float:
    """Calculate the documented PHF relation PHF = V/(4*V15).

    ``peak_15_min_volume_veh`` is the vehicle count in the peak 15-minute
    interval, not a rate in vehicles per hour. This relation is included in
    the supplied formula-reference CSV; the integrated Chapter 20 analyzer
    accepts PHF as an explicit input because the Chapter 12 source is not in
    the current verified document set.
    """
    if hourly_volume_veh_per_h <= 0 or peak_15_min_volume_veh <= 0:
        raise CalculationInputError("V y V15 deben ser mayores que cero.")
    phf = hourly_volume_veh_per_h / (4.0 * peak_15_min_volume_veh)
    if not 0 < phf <= 1:
        raise CalculationInputError("PHF calculado debe estar en el intervalo (0, 1].")
    return phf
