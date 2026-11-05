from importlib.metadata import version

from .limiting_mag import Telescope, is_object_observable, object_magnitude, smallest_scope

__version__ = version("maglimit")

__all__ = ["Telescope", "is_object_observable", "object_magnitude", "smallest_scope"]
