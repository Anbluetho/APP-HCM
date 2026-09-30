"""Structured user inputs collected by the initial Streamlit interface."""

from typing import TypedDict


class ProjectInfo(TypedDict):
    project_name: str
    analyst: str
    location: str
    data_origin: str


class FacilityInfo(TypedDict):
    facility_type: str


class GeometricInputs(TypedDict):
    segment_length_km: float | None
    lane_width_m: float | None
    shoulder_width_m: float | None
    lanes_per_direction: int | None
    lateral_clearance_m: float | None
    median_type: str | None


class TrafficInputs(TypedDict):
    tpda_veh_per_day: float | None
    k3_design_hour_factor: float | None
    direction_share_percent: float | None
    major_direction_percent: float | None
    peak_hour_factor: float | None
    trucks_percent: float | None
    recreational_vehicles_percent: float | None


class OperationalInputs(TypedDict):
    terrain: str | None
    highway_class: str | None


class ProcedureInputs(TypedDict):
    field_notes: str
    access_points_per_km: float | None
    no_passing_zones_percent: float | None
    base_free_flow_speed_km_per_h: float | None
    driver_population_factor: float | None


class AnalysisInput(TypedDict):
    project: ProjectInfo
    facility: FacilityInfo
    geometry: GeometricInputs
    traffic: TrafficInputs
    operation: OperationalInputs
    procedure_additional: ProcedureInputs
