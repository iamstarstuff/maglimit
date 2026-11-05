import astropy.units as u
import numpy as np
from astroquery.ipac.ned import Ned


class Telescope:
    """Takes in telescope parameters.

    Args:
        aperture: cross section of primary element in mm
        fstop: ratio of focal length and aperture.

    Returns:
        Telescope object

    Raises:
        ValueError: if aperture or fstop is not positive
    """
    def __init__(self, aperture, fstop):
        if aperture <= 0:
            raise ValueError(f"aperture must be positive, got {aperture}")
        if fstop <= 0:
            raise ValueError(f"fstop must be positive, got {fstop}")
        self.aperture = aperture*u.mm
        self.fstop = fstop

    def focal_length(self):
        """Calculates focal length using aperture and fstop values from Telescope class

        Returns:
            Focal length of telescope in mm.
        """
        return self.aperture*self.fstop

    def magnification(self, f_eyepiece):
        """To calculate magnification of the telescope

        Args:
            f_eyepiece: focal length of eyepiece in mm. eg: 10, 25, 32 ...

        Returns:
            x Magnification, rounded to 2 decimals
        """
        mag = self.focal_length()/(f_eyepiece*u.mm)
        return float(np.round(mag.to_value(u.dimensionless_unscaled), 2))

    def lim_mag(self):
        """Calculates limiting magnitude of telescope, i.e the faintest object that can be observed

        Returns:
            Limiting magnitude of telescope
        """
        return float(np.round(2 + 5*np.log10(self.aperture.to_value(u.mm)), 2))


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
