"""Structured, traceable results returned by the independent HCM engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CalculationResult:
    """Inputs, retrieved parameters, calculation trail, outcome, and warnings."""

    inputs: dict[str, object]
    parameters: dict[str, object]
    intermediate_results: dict[str, object]
    final_results: dict[str, object]
    warnings: tuple[str, ...]
    formula_references: tuple[str, ...]
