"""Heavy-vehicle adjustment calculation for two-lane highway segments."""

from calculations.exceptions import CalculationInputError


def calculate_heavy_vehicle_factor(
    trucks_percent: float, recreational_vehicles_percent: float,
    truck_equivalency: float, rv_equivalency: float,
) -> float:
    """Calculate fHV using HCM 2000 Chapter 20, Equation 20-4.

    Percentages are converted to decimal proportions. Equivalencies must come
    from Exhibit 20-9 for speed or Exhibit 20-10 for PTSF.
    """
    _validate_percent(trucks_percent, "Porcentaje de camiones")
    _validate_percent(recreational_vehicles_percent, "Porcentaje de RV")
    if trucks_percent + recreational_vehicles_percent > 100:
        raise CalculationInputError("Los porcentajes de camiones y RV no pueden sumar más de 100%.")
    if truck_equivalency < 1 or rv_equivalency < 1:
        raise CalculationInputError("Los equivalentes de vehículos pesados deben ser >= 1.")
    pt, pr = trucks_percent / 100.0, recreational_vehicles_percent / 100.0
    return 1.0 / (1.0 + pt * (truck_equivalency - 1.0) + pr * (rv_equivalency - 1.0))


def _validate_percent(value: float, name: str) -> None:
    """Validate a measured vehicle-class percentage in the 0–100 range."""
    if not 0 <= value <= 100:
        raise CalculationInputError(f"{name} debe estar entre 0 y 100%.")
