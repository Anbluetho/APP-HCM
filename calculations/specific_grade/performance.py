"""Performance measures for HCM 2000 directional two-lane segments."""

from __future__ import annotations

from itertools import product
from math import exp
from typing import Any

from calculations.exceptions import CalculationDataError, CalculationInputError


def calculate_directional_ats(
    free_flow_speed_km_per_h: float,
    analysis_flow_pc_per_h: float,
    opposing_flow_pc_per_h: float,
    no_passing_adjustment_km_per_h: float,
) -> float:
    """Calculate ATSd with HCM 2000 Chapter 20 Equation 20-15."""
    values = (free_flow_speed_km_per_h, analysis_flow_pc_per_h,
              opposing_flow_pc_per_h, no_passing_adjustment_km_per_h)
    if any(value < 0 for value in values):
        raise CalculationInputError("Los valores de ATS deben ser no negativos.")
    return free_flow_speed_km_per_h - 0.0125 * (
        analysis_flow_pc_per_h + opposing_flow_pc_per_h
    ) - no_passing_adjustment_km_per_h


def calculate_directional_base_ptsf(
    analysis_flow_pc_per_h: float, coefficient_a: float, coefficient_b: float,
) -> float:
    """Calculate BPTSFd from Equation 20-17 and Exhibit 20-21 coefficients."""
    if analysis_flow_pc_per_h < 0 or coefficient_b <= 0:
        raise CalculationInputError("El flujo PTSF debe ser no negativo y el coeficiente b positivo.")
    return 100.0 * (1.0 - exp(
        coefficient_a * (analysis_flow_pc_per_h ** coefficient_b)
    ))


def calculate_directional_ptsf(
    base_ptsf_percent: float, no_passing_adjustment_percent: float,
) -> float:
    """Calculate PTSFd using HCM 2000 Chapter 20 Equation 20-16."""
    ptsf = base_ptsf_percent + no_passing_adjustment_percent
    if not 0 <= ptsf <= 100:
        raise CalculationInputError(
            f"PTSF calculado ({ptsf:.3f} %) queda fuera de 0-100%; no se limita ni corrige automáticamente."
        )
    return ptsf


def interpolate_directional_no_passing_adjustment(
    records: list[dict[str, Any]], *, free_flow_speed_km_per_h: float,
    opposing_flow_pc_per_h: float, no_passing_zones_percent: float,
    value_field: str,
) -> float:
    """Interpolate an Exhibit 20-19 or 20-20 value on its three axes.

    The published endpoint categories are applied at the edges: opposing
    flow at/below the first row, flow at/above the last row, and no-passing
    percentages at/below 20% use their respective table endpoint. FFS must be
    inside the printed 70-110 km/h domain.
    """
    if not records:
        raise CalculationDataError("La tabla de ajuste por zonas de no rebase está vacía.")
    if no_passing_zones_percent == 0:
        # With no no-passing zone, that zone's adjustment is zero by definition.
        return 0.0
    ffs_values = sorted({float(row["ffs_kmh"]) for row in records})
    vo_values = sorted({float(row["opposing_flow_pcph"]) for row in records})
    np_values = sorted({float(row["no_passing_zones_pct"]) for row in records})
    if not ffs_values[0] <= free_flow_speed_km_per_h <= ffs_values[-1]:
        raise CalculationInputError(
            f"La FFS de {free_flow_speed_km_per_h:g} km/h queda fuera del dominio "
            f"tabulado {ffs_values[0]:g}-{ffs_values[-1]:g} km/h para fnp."
        )
    axes = [
        (ffs_values, free_flow_speed_km_per_h, False),
        (vo_values, opposing_flow_pc_per_h, True),
        (np_values, no_passing_zones_percent, True),
    ]
    brackets = [_axis_bracket(*axis) for axis in axes]
    grid = {
        (float(row["ffs_kmh"]), float(row["opposing_flow_pcph"]),
         float(row["no_passing_zones_pct"])): float(row[value_field])
        for row in records
    }
    corners = {}
    for point in product(*[(lo,) if lo == hi else (lo, hi) for lo, hi in brackets]):
        if point not in grid:
            raise CalculationDataError(
                f"La tabla no contiene el punto completo de interpolación {point}."
            )
        corners[point] = grid[point]
    return _interpolate_multilinear(brackets, axes, corners)


def lookup_ptsf_coefficients(
    records: list[dict[str, Any]], opposing_flow_pc_per_h: float,
) -> tuple[float, float]:
    """Interpolate coefficients a and b from HCM Exhibit 20-21 by opposing flow."""
    coords = sorted(float(row["opposing_flow_pcph"]) for row in records)
    if not coords:
        raise CalculationDataError("Exhibit 20-21 no contiene coeficientes.")
    low, high = _bracket(coords, opposing_flow_pc_per_h, clamp=True)
    by_flow = {float(row["opposing_flow_pcph"]): row for row in records}
    a = _linear(opposing_flow_pc_per_h, low, high, float(by_flow[low]["a"]), float(by_flow[high]["a"]))
    b = _linear(opposing_flow_pc_per_h, low, high, float(by_flow[low]["b"]), float(by_flow[high]["b"]))
    return a, b


def _axis_bracket(
    coords: list[float], value: float, clamp: bool,
) -> tuple[float, float]:
    return _bracket(coords, value, clamp=clamp)


def _bracket(
    coords: list[float], value: float, *, clamp: bool,
) -> tuple[float, float]:
    if value <= coords[0]:
        if clamp:
            return coords[0], coords[0]
        raise CalculationInputError(f"El valor {value:g} queda debajo del dominio tabulado {coords[0]:g}.")
    if value >= coords[-1]:
        if clamp:
            return coords[-1], coords[-1]
        raise CalculationInputError(f"El valor {value:g} excede el dominio tabulado {coords[-1]:g}.")
    if value in coords:
        return value, value
    for low, high in zip(coords, coords[1:]):
        if low < value < high:
            return low, high
    raise CalculationInputError(f"No se encontró intervalo tabulado para {value:g}.")


def _interpolate_multilinear(
    brackets: list[tuple[float, float]], axes: list[tuple[list[float], float, bool]],
    corners: dict[tuple[float, ...], float],
) -> float:
    """Interpolate a complete rectangular grid, including fixed axes."""
    values = corners
    for axis_index in reversed(range(len(brackets))):
        low, high = brackets[axis_index]
        if low == high:
            continue
        other_axes = [i for i in range(len(brackets)) if i != axis_index]
        reduced = {}
        for fixed in product(*[
            (brackets[i][0],) if brackets[i][0] == brackets[i][1]
            else (brackets[i][0], brackets[i][1])
            for i in other_axes
        ]):
            low_point = [0.0] * len(brackets)
            high_point = [0.0] * len(brackets)
            for i, value in zip(other_axes, fixed):
                low_point[i] = high_point[i] = value
            low_point[axis_index] = low
            high_point[axis_index] = high
            lower_value = values[tuple(low_point)]
            upper_value = values[tuple(high_point)]
            reduced[fixed] = _linear(axes[axis_index][1], low, high, lower_value, upper_value)
        values = reduced
        brackets = [brackets[i] for i in other_axes]
        axes = [axes[i] for i in other_axes]
    if len(values) != 1:
        raise CalculationDataError("No se pudo completar la interpolación de la tabla HCM.")
    return next(iter(values.values()))


def _linear(value: float, low: float, high: float, low_value: float, high_value: float) -> float:
    if low == high:
        return low_value
    return low_value + (value - low) / (high - low) * (high_value - low_value)
