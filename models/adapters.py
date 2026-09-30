"""Adapters between the Streamlit form contract and calculation models."""

from models.input_data import AnalysisInput, TrafficInputs
from models.two_lane_highway import TwoLaneHighwayInputs
from models.multilane_highway import MultilaneHighwayInputs
from calculations.design_hour_volume import calculate_design_hour_volume
from calculations.design_hour_volume import DesignHourVolume


def to_two_lane_highway_inputs(data: AnalysisInput) -> TwoLaneHighwayInputs:
    """Map validated form fields to the independent HCM calculation input.

    Raises:
        ValueError: If any field required by the calculation is missing.
    """
    traffic = data["traffic"]
    geometry = data["geometry"]
    operation = data["operation"]
    additional = data["procedure_additional"]
    demand = _design_hour_demand(traffic)
    required = {
        "major_direction_percent": traffic["major_direction_percent"],
        "peak_hour_factor": traffic["peak_hour_factor"],
        "trucks_percent": traffic["trucks_percent"],
        "recreational_vehicles_percent": traffic["recreational_vehicles_percent"],
        "terrain": operation["terrain"],
        "highway_class": operation["highway_class"],
        "segment_length_km": geometry["segment_length_km"],
        "lane_width_m": geometry["lane_width_m"],
        "shoulder_width_m": geometry["shoulder_width_m"],
        "access_points_per_km": additional["access_points_per_km"],
        "no_passing_zones_percent": additional["no_passing_zones_percent"],
        "base_free_flow_speed_km_per_h": additional["base_free_flow_speed_km_per_h"],
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError("Faltan entradas requeridas para HCM: " + ", ".join(missing))

    terrain = {"plano": "level", "ondulado": "rolling"}.get(str(operation["terrain"]))
    if terrain is None:
        raise ValueError("El motor de dos carriles solo tiene tablas documentadas para terreno plano/nivel u ondulado.")

    return TwoLaneHighwayInputs(
        hourly_volume_veh_per_h=demand.vhd_two_way_veh_per_h,
        peak_hour_factor=float(traffic["peak_hour_factor"]),
        major_direction_percent=float(traffic["major_direction_percent"]),
        trucks_percent=float(traffic["trucks_percent"]),
        recreational_vehicles_percent=float(traffic["recreational_vehicles_percent"]),
        terrain=terrain,
        highway_class=str(operation["highway_class"]),
        segment_length_km=float(geometry["segment_length_km"]),
        lane_width_m=float(geometry["lane_width_m"]),
        shoulder_width_m=float(geometry["shoulder_width_m"]),
        access_points_per_km=float(additional["access_points_per_km"]),
        no_passing_zones_percent=float(additional["no_passing_zones_percent"]),
        base_free_flow_speed_km_per_h=float(
            additional["base_free_flow_speed_km_per_h"]
        ),
        tpda_veh_per_day=demand.tpda_veh_per_day,
        k3_design_hour_factor=demand.k3_design_hour_factor,
        direction_share_percent=demand.direction_share_percent,
    )


def to_multilane_highway_inputs(data: AnalysisInput) -> MultilaneHighwayInputs:
    """Map validated form fields to the multilane engine input object."""
    traffic = data["traffic"]
    geometry = data["geometry"]
    operation = data["operation"]
    additional = data["procedure_additional"]
    demand = _design_hour_demand(traffic)
    required = {
        "major_direction_percent": traffic["major_direction_percent"],
        "peak_hour_factor": traffic["peak_hour_factor"],
        "trucks_percent": traffic["trucks_percent"],
        "recreational_vehicles_percent": traffic["recreational_vehicles_percent"],
        "terrain": operation["terrain"],
        "lanes_per_direction": geometry["lanes_per_direction"],
        "lane_width_m": geometry["lane_width_m"],
        "lateral_clearance_m": geometry["lateral_clearance_m"],
        "median_type": geometry["median_type"],
        "access_points_per_km": additional["access_points_per_km"],
        "base_free_flow_speed_km_per_h": additional["base_free_flow_speed_km_per_h"],
        "driver_population_factor": additional["driver_population_factor"],
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError("Faltan entradas requeridas para multicarril: " + ", ".join(missing))
    return MultilaneHighwayInputs(
        hourly_volume_two_way_veh_per_h=demand.vhd_two_way_veh_per_h,
        peak_hour_factor=float(traffic["peak_hour_factor"]),
        major_direction_percent=float(traffic["major_direction_percent"]),
        trucks_percent=float(traffic["trucks_percent"]),
        recreational_vehicles_percent=float(traffic["recreational_vehicles_percent"]),
        terrain=str(operation["terrain"]),
        lanes_per_direction=int(geometry["lanes_per_direction"]),
        lane_width_m=float(geometry["lane_width_m"]),
        lateral_clearance_m=float(geometry["lateral_clearance_m"]),
        median_type=str(geometry["median_type"]),
        access_points_per_km=float(additional["access_points_per_km"]),
        base_free_flow_speed_km_per_h=float(additional["base_free_flow_speed_km_per_h"]),
        driver_population_factor=float(additional["driver_population_factor"]),
    )


def _design_hour_demand(traffic: TrafficInputs) -> DesignHourVolume:
    """Return calculated VHD from the three required local demand inputs."""
    required = {
        "tpda_veh_per_day": traffic.get("tpda_veh_per_day"),
        "k3_design_hour_factor": traffic.get("k3_design_hour_factor"),
        "direction_share_percent": traffic.get("direction_share_percent"),
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError("Faltan datos para calcular VHD: " + ", ".join(missing))
    return calculate_design_hour_volume(
        float(required["tpda_veh_per_day"]),
        float(required["k3_design_hour_factor"]),
        float(required["direction_share_percent"]),
    )
