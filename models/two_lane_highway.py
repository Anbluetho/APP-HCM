"""Inputs for the HCM 2000 two-way, two-lane highway segment procedure."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TwoLaneHighwayInputs:
    """Validated units and field data required by the implemented procedure.

    This request is separate from the preliminary Streamlit form contract. It
    represents one extended, two-way segment and requires the inputs that the
    HCM Chapter 20 worksheet/example actually uses.
    """

    hourly_volume_veh_per_h: float
    peak_hour_factor: float
    major_direction_percent: float
    trucks_percent: float
    recreational_vehicles_percent: float
    terrain: str
    highway_class: str
    segment_length_km: float
    lane_width_m: float
    shoulder_width_m: float
    access_points_per_km: float
    no_passing_zones_percent: float
    base_free_flow_speed_km_per_h: float

