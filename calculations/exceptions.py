"""Errors raised for invalid inputs or unavailable HCM procedure data."""


class CalculationError(ValueError):
    """Base class for calculation requests that cannot be safely evaluated."""


class CalculationInputError(CalculationError):
    """An input is invalid or outside the documented procedure/table domain."""


class CalculationDataError(CalculationError):
    """A required, verified HCM table value could not be retrieved."""
