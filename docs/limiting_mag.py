import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.ipac.ned import Ned
from astroquery.sdss import SDSS
from astroquery.vizier import Vizier




class Telescope():
    """Takes in telescope parameters.

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
            aperture: cross section of primary mirror from Telescope class in mm
            fstop: f ratio from Telescope class

        Returns:
            Focal length of telescope.
        """
        return self.aperture*self.fstop

    def magnification(self,f_eyepiece):
        """To calculate magnification of the telescope

        Args:
            f_eyepiece: focal length of eyepiece. eg: 10mm, 25mm, 32mm ... 

        Returns:
            x Magnification 
        """
        return int((self.focal_length()/f_eyepiece*u.mm).value)

    def lim_mag(self):
        """Calculates limiting magnitude of telescope, i.e the faintest object that can be observed

        Args:
            aperture: from Telescope class

        Returns:
            Limiting magnitude of telescope
        """
        return np.round(2 + 5*np.log10(self.aperture.value),2)


def is_object_observable(obj,lm):
    """Determines if an astronomical object is observed by the telescope

    Args:
        obj = Telescope object from the class Telescope
        lm = limiting magnitude from Telescope.lim_mag()

    Returns:
        True if object can be observed else False
        Prints limiting magnitude of telescope and magnitude value of object.
    """
    ob = float(Ned.query_object(obj)["Magnitude and Filter"][0])
    print(f"Limiting magnitude of scope is {lm} and magnitude of {obj} is {ob}")
    if ob > lm:
        return False
    else:
        return True

def smallest_scope(obj,fs):
    """Estimates the smallest scope required to observe an object

    Args:
        obj: Astronomical object (Messier or NGC Catalogue)
        fs: desired f stop ratio 

    Returns:
        ob: Object magnitude using the Ned catalogue
        ap: Minimum required Aperture of the telescope to just see the object
        fl: Minimum required Focal length of the telescope to just see the object
    """
    ob = float(Ned.query_object(obj)["Magnitude and Filter"][0])
    ap = np.round(10**((ob-2)/5),2)
    fl = np.round(fs*ap,2)
    return ob,ap,fl