"""Local TPDA-to-design-hour demand conversion, separate from HCM factors."""

from dataclasses import dataclass
from math import isfinite

from calculations.exceptions import CalculationInputError


@dataclass(frozen=True)
class DesignHourVolume:
    """Hourly volumes derived from TPDA, K3, and HCM Exhibit 20-12 split."""

    tpda_veh_per_day: float
    k3_design_hour_factor: float
    major_direction_percent: float
    analysis_direction_is_major: bool
    analysis_direction_share_percent: float
    vhd_two_way_veh_per_h: float
    vhd_analysis_direction_veh_per_h: float
    vhd_opposing_direction_veh_per_h: float


def calculate_design_hour_volume(
    tpda_veh_per_day: float,
    k3_design_hour_factor: float,
    major_direction_percent: float,
    *,
    analysis_direction_is_major: bool = True,
) -> DesignHourVolume:
    """Convert TPDA to total and directional design-hour volumes.

    This is a jurisdiction/design-demand conversion before the HCM procedure,
    not an HCM 2000 adjustment factor. The supplied project references express
    the relationship as VHD = TPDA*K. The directional share used here is the
    share selected from HCM 2000 Exhibit 20-12, never a second D input.
    """
    values = {
        "TPDA": tpda_veh_per_day,
        "K3": k3_design_hour_factor,
        "Categoría direccional Exhibit 20-12": major_direction_percent,
    }
    for name, value in values.items():
        if not isinstance(value, (int, float)) or not isfinite(value):
            raise CalculationInputError(f"{name} debe ser un valor numérico finito.")
    if tpda_veh_per_day <= 0:
        raise CalculationInputError("El TPDA debe ser mayor que cero.")
    if not 0 < k3_design_hour_factor <= 1:
        raise CalculationInputError("K3 debe ser una fracción mayor que 0 y menor o igual que 1.")
    if major_direction_percent not in {50, 60, 70, 80, 90}:
        raise CalculationInputError(
            "Seleccione una categoría tabulada en Exhibit 20-12: 50/50, 60/40, 70/30, 80/20 o 90/10."
        )
    if not isinstance(analysis_direction_is_major, bool):
        raise CalculationInputError("Indique si el sentido analizado corresponde al mayor o menor flujo.")

    vhd = tpda_veh_per_day * k3_design_hour_factor
    direction_share = float(
        major_direction_percent if analysis_direction_is_major else 100 - major_direction_percent
    )
    analysis_volume = vhd * direction_share / 100.0
    return DesignHourVolume(
        tpda_veh_per_day=float(tpda_veh_per_day),
        k3_design_hour_factor=float(k3_design_hour_factor),
        major_direction_percent=float(major_direction_percent),
        analysis_direction_is_major=analysis_direction_is_major,
        analysis_direction_share_percent=direction_share,
        vhd_two_way_veh_per_h=vhd,
        vhd_analysis_direction_veh_per_h=analysis_volume,
        vhd_opposing_direction_veh_per_h=vhd - analysis_volume,
    )
