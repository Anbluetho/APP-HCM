"""Shared provenance types for distinguishing the origin of analysis values."""

from enum import Enum


class ValueSource(str, Enum):
    """Origin category for an input, lookup value, or calculated result."""

    USER_INPUT = "user_input"
    HCM_2000 = "hcm_2000_table"
    ECUADOR = "ecuador_parameter"
    CALCULATED = "calculated"
