from importlib.metadata import version

from .catalogue import CatalogueObject, find_object
from .limiting_mag import is_object_observable, object_magnitude, smallest_scope
from .planner import explain
from .site import Site, bortle_to_sqm, naked_eye_limit
from .telescope import Eyepiece, Telescope

__version__ = version("maglimit")

__all__ = [
    "CatalogueObject",
    "Eyepiece",
    "Site",
    "Telescope",
    "bortle_to_sqm",
    "explain",
    "find_object",
    "is_object_observable",
    "naked_eye_limit",
    "object_magnitude",
    "smallest_scope",
]
