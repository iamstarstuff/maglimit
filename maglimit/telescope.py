import math
from dataclasses import dataclass

import astropy.units as u
import numpy as np


def _check_positive(name, value):
    """Raises ValueError unless value is a positive, finite number
    """
    if not (math.isfinite(value) and value > 0):
        raise ValueError(f"{name} must be positive, got {value}")


@dataclass(frozen=True)
class Eyepiece:
    """Takes in eyepiece parameters.

    Args:
        focal_length: focal length of eyepiece in mm
        afov: apparent field of view in degrees

    Raises:
        ValueError: if a value is not physically possible
    """
    focal_length: float
    afov: float = 52.0

    def __post_init__(self):
        _check_positive("eyepiece focal length", self.focal_length)
        _check_positive("apparent field", self.afov)
        if self.afov > 180:
            raise ValueError(f"apparent field must be at most 180 degrees, got {self.afov}")


def _as_eyepiece(eyepiece):
    """Returns an Eyepiece, wrapping a plain focal length if needed
    """
    return eyepiece if isinstance(eyepiece, Eyepiece) else Eyepiece(eyepiece)


class Telescope:
    """Takes in telescope parameters.

    Args:
        aperture: cross section of primary element in mm
        fstop: ratio of focal length and aperture.
        eyepieces: eyepieces owned, as focal lengths in mm or Eyepiece objects
        obstruction: central obstruction as a fraction of the aperture's diameter
        transmission: fraction of light that gets through the optics

    Returns:
        Telescope object

    Raises:
        ValueError: if a value is not physically possible
    """
    def __init__(self, aperture, fstop, eyepieces=(), obstruction=0.0, transmission=0.8):
        _check_positive("aperture", aperture)
        _check_positive("fstop", fstop)
        if not 0 <= obstruction < 1:
            raise ValueError(f"obstruction must be from 0 up to 1, got {obstruction}")
        if not 0 < transmission <= 1:
            raise ValueError(f"transmission must be above 0 and at most 1, got {transmission}")
        self.aperture = aperture*u.mm
        self.fstop = fstop
        self.eyepieces = tuple(_as_eyepiece(eyepiece) for eyepiece in eyepieces)
        self.obstruction = obstruction
        self.transmission = transmission

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
