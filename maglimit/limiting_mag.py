import astropy.units as u
import numpy as np
from astroquery.ipac.ned import Ned

from .telescope import Telescope  # noqa: F401  (kept importable from here since v0.1)


def object_magnitude(obj):
    """Queries the NED catalogue for the magnitude of an astronomical object

    Args:
        obj: Name of the object (Messier or NGC Catalogue), eg: 'M31', 'NGC 244'

    Returns:
        Magnitude of the object

    Raises:
        ValueError: if NED has no magnitude for the object
    """
    value = Ned.query_object(obj)["Magnitude and Filter"][0]
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"NED has no magnitude for {obj!r} (got {value!r})") from None


def is_object_observable(obj, lm):
    """Determines if an astronomical object is observed by the telescope

    Args:
        obj: Name of the object (Messier or NGC Catalogue), eg: 'M31'
        lm: limiting magnitude from Telescope.lim_mag()

    Returns:
        True if object can be observed else False
        Prints limiting magnitude of telescope and magnitude value of object.
    """
    ob = object_magnitude(obj)
    print(f"Limiting magnitude of scope is {lm} and magnitude of {obj} is {ob}")
    return ob <= lm


def smallest_scope(obj, fs):
    """Estimates the smallest scope required to observe an object

    Args:
        obj: Astronomical object (Messier or NGC Catalogue)
        fs: desired f stop ratio

    Returns:
        ob: Object magnitude using the Ned catalogue
        ap: Minimum required Aperture of the telescope to just see the object, in mm
        fl: Minimum required Focal length of the telescope to just see the object, in mm
    """
    ob = object_magnitude(obj)
    ap = np.round(10**((ob-2)/5), 2)*u.mm
    fl = np.round(fs*ap, 2)
    return ob, ap, fl
