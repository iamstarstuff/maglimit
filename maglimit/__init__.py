from importlib.metadata import version

from .limiting_mag import is_object_observable, object_magnitude, smallest_scope
from .site import Site, bortle_to_sqm, naked_eye_limit
from .telescope import Eyepiece, Telescope

__version__ = version("maglimit")

__all__ = [
    "Eyepiece",
    "Site",
    "Telescope",
    "bortle_to_sqm",
    "is_object_observable",
    "naked_eye_limit",
    "object_magnitude",
    "smallest_scope",
]
