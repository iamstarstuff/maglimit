"""Contrast-threshold visibility model after Crumey (2014).

Crumey, A. (2014), "Human contrast threshold and astronomical visibility",
MNRAS 442, 2600. https://arxiv.org/abs/1405.4209

The model is a closed-form fit to Blackwell's (1946) threshold data for the
dark-adapted (scotopic) eye, extended to telescopic viewing. Equation numbers
in the docstrings refer to the paper. Everything here takes and returns plain
numbers, so the module ports directly to other languages.

Arguments shared by the functions:

- aperture: telescope aperture in mm
- magnification: telescope magnification
- sqm: sky brightness in mag/arcsec²
- eye_pupil: the paper's pupil diameter in mm. It is fitted together with the
  field factor, so it isn't a free observer setting; public code passes 7.0
  and models a smaller eye with used_aperture()
- throughput: fraction of light the telescope passes (1/Ft in the paper)
- field_factor: Crumey's F, the factor between laboratory and field thresholds
"""
import math

# Illuminance of a magnitude 0 star in lux (Eq. 3)
Z = 2.54e-6
# One square arcsecond in steradians
ARCSEC2 = (math.pi/(180*3600))**2
# Scotopic constants (Eqs. 26, 37, 44)
R1, R2 = 6.505e-4, -8.461e-4
K1, K2 = 7.633e-3, -7.174e-3
Q = 0.6
# Below this background in cd/m² thresholds no longer improve (zero-background cut-off)
CUT_OFF = 1e-5

VERDICT_BANDS = ((2.0, "easy"), (1.0, "moderate"), (0.5, "challenging"), (0.0, "very hard"))


def sky_luminance(mu):
    """Converts a surface brightness to a luminance

    Args:
        mu: surface brightness in mag/arcsec²

    Returns:
        Luminance in cd/m²
    """
    return Z/ARCSEC2*10**(-0.4*mu)


def surface_brightness(magnitude, major, minor):
    """Calculates the mean surface brightness of an elliptical object

    Args:
        magnitude: integrated magnitude
        major: major axis in arcmin
        minor: minor axis in arcmin

    Returns:
        Mean surface brightness in mag/arcsec²
    """
    return magnitude + 2.5*math.log10(math.pi/4*major*minor*3600)


def used_aperture(aperture, magnification, eye_pupil):
    """Calculates the part of the aperture whose light gets into the eye

    When the exit pupil is wider than the eye's pupil, the outer light is lost,
    as if the telescope were smaller.

    Args:
        aperture: telescope aperture in mm
        magnification: telescope magnification
        eye_pupil: diameter of the observer's pupil in mm

    Returns:
        Effective aperture in mm
    """
    return aperture*min(1.0, eye_pupil/(aperture/magnification))


def _adaptation(aperture, magnification, sqm, eye_pupil, throughput):
    """Returns the exit pupil terms and the background seen in the eyepiece (Eq. 66)
    """
    exit_pupil = aperture/magnification
    d_min, d_max = min(exit_pupil, eye_pupil), max(exit_pupil, eye_pupil)
    background = (d_min/eye_pupil)**2*sky_luminance(sqm)*throughput
    return d_min, d_max, max(background, CUT_OFF)


def star_limit(aperture, magnification, sqm, eye_pupil=7.0, throughput=0.8, field_factor=2.0):
    """Calculates the faintest star visible through a telescope

    Uses Eq. 68 for the threshold of a point source, with the background held at
    the zero-background cut-off (Eq. 71) once the eyepiece makes it darker.

    Returns:
        Limiting magnitude
    """
    _d_min, d_max, background = _adaptation(aperture, magnification, sqm, eye_pupil, throughput)
    ricco = (R1*background**-0.25 + R2)**2
    phi = math.sqrt(2)*field_factor
    increment = (d_max/aperture)**2/throughput*phi*background*ricco
    return -2.5*math.log10(increment/Z)


def visibility_margin(mu_object, area, aperture, magnification, sqm, eye_pupil=7.0,
                      throughput=0.8, field_factor=2.0):
    """Calculates how far an extended object is above the visibility threshold

    Compares the brightness the object adds in the eyepiece with the threshold
    increment for its apparent size (Eqs. 77-80).

    Args:
        mu_object: mean surface brightness of the object in mag/arcsec²
        area: area of the object in arcmin²

    Returns:
        Margin in magnitudes; positive means visible
    """
    d_min, _, background = _adaptation(aperture, magnification, sqm, eye_pupil, throughput)
    ricco = (R1*background**-0.25 + R2)**2
    large = K1*background**-0.25 + K2
    phi = math.sqrt(2)*field_factor
    object_increment = sky_luminance(mu_object)*(d_min/eye_pupil)**2*throughput
    apparent_area = area*3600*ARCSEC2*magnification**2
    threshold = background*phi*((ricco/apparent_area)**Q + large**Q)**(1/Q)
    return 2.5*math.log10(object_increment/threshold)


def verdict(margin):
    """Grades a visibility margin

    Args:
        margin: magnitudes above threshold

    Returns:
        One of "easy", "moderate", "challenging", "very hard" or "not visible"
    """
    for edge, label in VERDICT_BANDS:
        if margin >= edge:
            return label
    return "not visible"
