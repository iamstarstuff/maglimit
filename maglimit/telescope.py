import math
from dataclasses import dataclass

import astropy.units as u
import numpy as np

from .site import naked_eye_limit


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

    def _magnification(self, eyepiece):
        """Unrounded magnification with an Eyepiece
        """
        return self.focal_length().to_value(u.mm)/eyepiece.focal_length

    def magnification(self, f_eyepiece):
        """To calculate magnification of the telescope

        Args:
            f_eyepiece: focal length of eyepiece in mm (eg: 10, 25, 32 ...) or an Eyepiece

        Returns:
            x Magnification, rounded to 2 decimals
        """
        return round(self._magnification(_as_eyepiece(f_eyepiece)), 2)

    def exit_pupil(self, eyepiece):
        """Calculates the width of the beam of light leaving the eyepiece

        Args:
            eyepiece: focal length of eyepiece in mm or an Eyepiece

        Returns:
            Exit pupil in mm, rounded to 2 decimals
        """
        return round(_as_eyepiece(eyepiece).focal_length/self.fstop, 2)

    def true_field(self, eyepiece):
        """Calculates how much sky is visible through an eyepiece

        Args:
            eyepiece: focal length of eyepiece in mm or an Eyepiece

        Returns:
            True field of view in degrees, rounded to 2 decimals
        """
        eyepiece = _as_eyepiece(eyepiece)
        return round(eyepiece.afov/self._magnification(eyepiece), 2)

    def min_magnification(self, eye_pupil=7.0):
        """Calculates the lowest magnification that uses the whole aperture

        Args:
            eye_pupil: diameter of the observer's dark-adapted pupil in mm

        Returns:
            Minimum useful magnification, rounded to 2 decimals
        """
        return round(self.aperture.to_value(u.mm)/eye_pupil, 2)

    def max_magnification(self):
        """Estimates the highest useful magnification, about twice the aperture in mm

        Returns:
            Maximum useful magnification, rounded to 2 decimals
        """
        return round(2*self.aperture.to_value(u.mm), 2)

    def dawes_limit(self):
        """Calculates the closest double star the telescope can separate

        Returns:
            Dawes limit in arcseconds, rounded to 2 decimals
        """
        return round(116/self.aperture.to_value(u.mm), 2)

    def lim_mag(self):
        """Calculates limiting magnitude of telescope, i.e the faintest object that can be observed

        Returns:
            Limiting magnitude of telescope
        """
        return float(np.round(2 + 5*np.log10(self.aperture.to_value(u.mm)), 2))

    def sky_lim_mag(self, site, eyepiece=None, eye_pupil=7.0):
        """Estimates the faintest star visible from a site, taking the sky into account

        A simplified model after Schaefer (1990). The eyepiece dims the sky background,
        so the eye works as if under a darker sky, and the star gains all the light the
        aperture collects. Light in an exit pupil wider than the eye is lost.

        Args:
            site: Site the telescope is used at
            eyepiece: focal length of eyepiece in mm or an Eyepiece. If None, assumes low
                power, with the exit pupil matching the eye
            eye_pupil: diameter of the observer's dark-adapted pupil in mm

        Returns:
            Limiting magnitude, rounded to 2 decimals
        """
        throughput = self.transmission*(1 - self.obstruction**2)
        exit_pupil = eye_pupil
        if eyepiece is not None:
            exit_pupil = _as_eyepiece(eyepiece).focal_length/self.fstop
        used_aperture = self.aperture.to_value(u.mm)*min(1, eye_pupil/exit_pupil)
        exit_pupil = min(exit_pupil, eye_pupil)
        sky = site.sqm - 2.5*math.log10(throughput*(exit_pupil/eye_pupil)**2)
        gain = 2.5*math.log10(throughput*used_aperture**2/eye_pupil**2)
        return round(naked_eye_limit(sky) + gain, 2)
