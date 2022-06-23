import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.ipac.ned import Ned
from astroquery.sdss import SDSS
from astroquery.vizier import Vizier




class Telescope():
    """Put in telescope parameters.

    Args:
        aperture: cross section of primary element in mm
        fstop: ratio of focal length and aperture.

    Returns:
        Telescope object
    """
    def __init__(self, aperture, fstop):
        self.aperture = aperture*u.mm
        self.fstop = fstop

    def focal_length(self):
        """Calculates focal length using aperture and fstop values from Telescope class

        Args:
            None

        Returns:
            Focal length of telescope.
        """
        return self.aperture*self.fstop

    def magnification(self,f_eyepiece):
        return int((self.focal_length()/f_eyepiece*u.mm).value)

    def lim_mag(self):
        return np.round(2 + 5*np.log10(self.aperture.value),2)


def is_object_observable(obj,lm):
    ob = float(Ned.query_object(obj)["Magnitude and Filter"][0])
    print(f"Limiting magnitude of scope is {lm} and magnitude of {obj} is {ob}")
    if ob > lm:
        return False
    else:
        return True