"""LOS classification using the registered HCM 2000 criteria table."""

from calculations.exceptions import CalculationInputError, CalculationDataError


def classify_level_of_service(
    highway_class: str, ptsf_percent: float, ats_km_per_h: float | None,
    criteria_records: list[dict[str, str]],
) -> str:
    """Classify LOS from Exhibit 20-2 or 20-4 records; HCM 2000 Chapter 20.

    Each performance measure is classified against the ranges in the verified
    CSV; Class I LOS is the worse of PTSF and ATS. Capacity LOS F is handled by
    ``calculations.capacity`` before this function is called.
    """
    if highway_class not in {"I", "II"}:
        raise CalculationInputError("La clase HCM debe ser I o II.")
    if not 0 <= ptsf_percent <= 100:
        raise CalculationInputError("PTSF debe estar entre 0 y 100%.")
    if highway_class == "I" and (ats_km_per_h is None or ats_km_per_h < 0):
        raise CalculationInputError("La clase I requiere ATS no negativa.")
    rows = [r for r in criteria_records if r.get("highway_class") == highway_class]
    ptsf_los = _classify_range_measure(ptsf_percent, rows, "PTSF_percent", increasing=True)
    if highway_class == "II":
        return ptsf_los
    assert ats_km_per_h is not None
    ats_los = _classify_range_measure(ats_km_per_h, rows, "ATS_kmh", increasing=False)
    return max((ptsf_los, ats_los), key="ABCDEF".index)


def _classify_range_measure(
    value: float, rows: list[dict[str, str]], field: str, *, increasing: bool,
) -> str:
    """Assign one letter by parsing the documented interval expressions."""
    from re import findall

    ordered = sorted(rows, key=lambda r: "ABCDEF".index(r["LOS"]))
    for row in ordered:
        criterion = row.get(field, "").strip()
        if not criterion or criterion == "flow_exceeds_capacity":
            continue
        bounds = [float(part) for part in findall(r"\d+(?:\.\d+)?", criterion)]
        if criterion.startswith("<="):
            matched = value <= bounds[0]
        elif criterion.startswith(">") and len(bounds) == 1:
            matched = value > bounds[0]
        elif criterion.startswith(">") and len(bounds) == 2:
            matched = bounds[0] < value <= bounds[1]
        else:
            raise CalculationDataError(f"Criterio LOS no reconocido: {criterion!r}.")
        if matched:
            return row["LOS"]
    raise CalculationDataError(f"No se pudo clasificar {field}={value} con la tabla registrada.")
