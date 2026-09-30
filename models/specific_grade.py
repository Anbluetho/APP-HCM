"""Input contract for HCM 2000 specific-grade directional analysis."""

from dataclasses import dataclass
from typing import Literal


GradeDirection = Literal["upgrade", "downgrade"]


@dataclass(frozen=True)
class SpecificGradeInputs:
    """Measured project inputs for one direction on a specific grade.

    All percentages are entered as percentages from 0 to 100. The UI supplies
    TPDA/K3 and the Exhibit 20-12 category; the model derives hourly vehicle
    volumes before HCM factors. The caller states whether the analyzed grade is
    in the major or minor flow direction;
    direct callers may continue to provide observed directional hourly volumes.
    """

    analysis_grade_direction: GradeDirection
    grade_percent: float
    grade_length_km: float
    analysis_volume_veh_per_h: float | None
    opposing_volume_veh_per_h: float | None
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
    tpda_veh_per_day: float | None = None
    k3_design_hour_factor: float | None = None
    major_direction_percent: float | None = None
    analysis_direction_is_major: bool | None = None
