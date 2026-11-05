from importlib.metadata import version

from .limiting_mag import is_object_observable, object_magnitude, smallest_scope
from .telescope import Eyepiece, Telescope

__version__ = version("maglimit")

__all__ = ["Eyepiece", "Telescope", "is_object_observable", "object_magnitude", "smallest_scope"]
