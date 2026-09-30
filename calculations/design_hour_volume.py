"""Local TPDA-to-design-hour demand conversion, separate from HCM factors."""

from dataclasses import dataclass
from math import isfinite

from calculations.exceptions import CalculationInputError


@dataclass(frozen=True)
class DesignHourVolume:
    """Hourly traffic volumes derived from TPDA, K3, and a directional share."""

    tpda_veh_per_day: float
    k3_design_hour_factor: float
    direction_share_percent: float
    vhd_two_way_veh_per_h: float
    vhd_analysis_direction_veh_per_h: float
    vhd_opposing_direction_veh_per_h: float


def calculate_design_hour_volume(
    tpda_veh_per_day: float,
    k3_design_hour_factor: float,
    direction_share_percent: float,
) -> DesignHourVolume:
    """Convert TPDA to total and directional design-hour volumes.

    This is a jurisdiction/design-demand conversion before the HCM procedure,
    not an HCM 2000 adjustment factor. The supplied project references express
    the relationship as VHD = TPDA*K and VHDD = TPDA*K*D.
    """
    values = {
        "TPDA": tpda_veh_per_day,
        "K3": k3_design_hour_factor,
        "D": direction_share_percent,
    }
    for name, value in values.items():
        if not isinstance(value, (int, float)) or not isfinite(value):
            raise CalculationInputError(f"{name} debe ser un valor numérico finito.")
    if tpda_veh_per_day <= 0:
        raise CalculationInputError("El TPDA debe ser mayor que cero.")
    if not 0 < k3_design_hour_factor <= 1:
        raise CalculationInputError("K3 debe ser una fracción mayor que 0 y menor o igual que 1.")
    if not 0 <= direction_share_percent <= 100:
        raise CalculationInputError("D debe estar entre 0 y 100 %.")

    vhd = tpda_veh_per_day * k3_design_hour_factor
    analysis_volume = vhd * direction_share_percent / 100.0
    return DesignHourVolume(
        tpda_veh_per_day=float(tpda_veh_per_day),
        k3_design_hour_factor=float(k3_design_hour_factor),
        direction_share_percent=float(direction_share_percent),
        vhd_two_way_veh_per_h=vhd,
        vhd_analysis_direction_veh_per_h=analysis_volume,
        vhd_opposing_direction_veh_per_h=vhd - analysis_volume,
    )
