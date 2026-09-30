"""Validated inputs for an extended multilane-highway segment."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MultilaneHighwayInputs:
    """User inputs for one directional HCM multilane segment analysis."""

    hourly_volume_two_way_veh_per_h: float
    peak_hour_factor: float
    major_direction_percent: float
    trucks_percent: float
    recreational_vehicles_percent: float
    terrain: str
    lanes_per_direction: int
    lane_width_m: float
    lateral_clearance_m: float
    median_type: str
    access_points_per_km: float
    base_free_flow_speed_km_per_h: float
    driver_population_factor: float
