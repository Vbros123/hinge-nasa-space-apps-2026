"""Hinge scientific engine: crop feasibility, FAO-56 ET0, bounded soil-water bucket, historical replay."""
MODEL_VERSION = "screening-v2"


class HingeError(Exception):
    """Base class."""


class MissingInputError(HingeError):
    """A required scientific input is absent or contains gaps. Never replaced by zero."""


class InvalidInputError(HingeError):
    """An input violates physical or schema constraints."""


class MassBalanceError(HingeError):
    """A simulation invariant (mass balance or storage bounds) failed; results must not be exported."""
