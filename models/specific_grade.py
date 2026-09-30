"""Input contract for HCM 2000 specific-grade directional analysis."""

from dataclasses import dataclass
from typing import Literal


GradeDirection = Literal["upgrade", "downgrade"]


@dataclass(frozen=True)
class SpecificGradeInputs:
    """Measured project inputs for one direction on a specific grade.

    All percentages are entered as percentages from 0 to 100. Volumes are
    hourly vehicle volumes, not passenger-car-equivalent flow rates.
    """

    analysis_grade_direction: GradeDirection
    grade_percent: float
    grade_length_km: float
    analysis_volume_veh_per_h: float
    opposing_volume_veh_per_h: float
    peak_hour_factor: float
    analysis_trucks_percent: float
    analysis_rvs_percent: float
    opposing_trucks_percent: float
    opposing_rvs_percent: float
    highway_class: str
    lane_width_m: float
    shoulder_width_m: float
    access_points_per_km: float
    no_passing_zones_percent: float
    base_free_flow_speed_analysis_km_per_h: float
    downhill_crawl_condition: bool | None = None
    downhill_trucks_at_crawl_percent: float | None = None
    downhill_truck_crawl_speed_km_per_h: float | None = None
    base_free_flow_speed_opposing_km_per_h: float | None = None
