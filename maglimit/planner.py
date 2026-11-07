"""Answers "can I see this object with this telescope under this sky?"
"""
import math

from .catalogue import find_object
from .telescope import _check_eye_pupil
from .visibility import star_limit, surface_brightness, used_aperture, verdict, visibility_margin

# Types also tested as a bright core holding half the light in a quarter of the
# diameter. A calibrated rule, not derived: catalogue sizes of galaxies and
# clusters reach far past what the eye sees.
CORE_TYPES = {"G", "GPair", "GTrpl", "GGroup", "GCl", "Cl+N"}
CORE_LIGHT, CORE_AREA = 0.5, 1/16
NEBULA_TYPES = {"HII", "Neb", "EmN", "RfN", "SNR"}
# Crumey's sky-spectrum correction holds for skies at least this dark
DARKEST_RELIABLE_SQM = 19.0
# Exit pupils in mm tried when the telescope has no eyepieces listed
TRIAL_EXIT_PUPILS = (7, 5, 3, 2, 1)
# The model is always called with this pupil; see Telescope.sky_lim_mag
MODEL_PUPIL = 7.0
ASSUMES = ["object at the zenith, no Moon", "no filter", "uniform brightness over the object"]


def _candidates(telescope, eye_pupil):
    """Returns (magnification, eyepiece focal length or None) pairs to try
    """
    aperture = telescope._aperture_mm()
    if telescope.eyepieces:
        options = [(telescope._magnification(e), e.focal_length) for e in telescope.eyepieces]
    else:
        pupils = dict.fromkeys(min(p, eye_pupil) for p in TRIAL_EXIT_PUPILS)
        options = [(aperture/p, None) for p in pupils]
    usable = [o for o in options if o[0] <= telescope.max_magnification()]
    return usable or options


def _margins(obj, telescope, sqm, magnification, eye_pupil, field_factor):
    """Returns (margin, seen_as) pairs for one magnification
    """
    aperture = used_aperture(telescope._aperture_mm(), magnification, eye_pupil)
    model = {"sqm": sqm, "eye_pupil": MODEL_PUPIL, "throughput": telescope.throughput(),
                 "field_factor": field_factor}
    if "no_size" in obj.flags:
        return [(star_limit(aperture, magnification, **model) - obj.magnitude, "point source")]
    area = math.pi/4*obj.major_axis*obj.minor_axis
    mu = surface_brightness(obj.magnitude, obj.major_axis, obj.minor_axis)
    margins = [(visibility_margin(mu, area, aperture, magnification, **model), "whole object")]
    if obj.type in CORE_TYPES:
        core_mu = mu - 2.5*math.log10(CORE_LIGHT/CORE_AREA)
        margins.append((visibility_margin(core_mu, area*CORE_AREA, aperture, magnification,
                                          **model), "bright core"))
    return margins


def _reasons(obj, sqm):
    """Returns the reasons to trust the answer less
    """
    reasons = []
    if obj.type in NEBULA_TYPES:
        reasons.append("catalogue magnitudes for nebulae are unreliable, and filters aren't "
                       "modelled")
    if "magnitude_estimated" in obj.flags:
        reasons.append("magnitude estimated from blue magnitude")
    if "no_size" in obj.flags:
        reasons.append("no size in the catalogue, so treated as a point source")
    if sqm < DARKEST_RELIABLE_SQM:
        reasons.append("sky too bright for the model's assumptions")
    return reasons


def explain(name, telescope, site, eye_pupil=7.0, field_factor=2.0):
    """Explains how well an object can be seen with a telescope from a site

    Tries each eyepiece (or a range of exit pupils if none are listed) and reports
    the best one.

    Args:
        name: object name, such as "M31", "NGC 224" or "Andromeda Galaxy"
        telescope: Telescope used
        site: Site observed from
        eye_pupil: diameter of the observer's dark-adapted pupil in mm
        field_factor: Crumey's factor between laboratory and field thresholds

    Returns:
        Dictionary of plain values: the object, its surface brightness, the margin
        above threshold in magnitudes, a graded verdict, how it is seen, the best
        magnification and eyepiece, a confidence level with reasons, and what the
        answer assumes

    Raises:
        ValueError: if the object isn't found or has no magnitude, or a value is impossible
    """
    _check_eye_pupil(eye_pupil)
    obj = find_object(name)
    if obj.magnitude is None:
        raise ValueError(f"{obj.name} has no magnitude in the catalogue")
    sqm = float(site.sqm)
    best = None
    for magnification, eyepiece in _candidates(telescope, eye_pupil):
        for margin, seen_as in _margins(obj, telescope, sqm, magnification, eye_pupil,
                                        field_factor):
            if best is None or margin > best[0]:
                best = (margin, seen_as, magnification, eyepiece)
    margin, seen_as, magnification, eyepiece = best
    margin = round(margin, 2)
    reasons = _reasons(obj, sqm)
    sb = None
    if "no_size" not in obj.flags:
        sb = round(surface_brightness(obj.magnitude, obj.major_axis, obj.minor_axis), 2)
    return {
        "object": {
            "name": obj.name,
            "messier": obj.messier,
            "type": obj.type,
            "magnitude": obj.magnitude,
            "major_axis": obj.major_axis,
            "minor_axis": obj.minor_axis,
            "common_names": list(obj.common_names),
        },
        "surface_brightness": sb,
        "sky_sqm": sqm,
        "margin": margin,
        "verdict": verdict(margin),
        "seen_as": seen_as,
        "best_magnification": round(magnification, 2),
        "best_exit_pupil": round(telescope._aperture_mm()/magnification, 2),
        "best_eyepiece": eyepiece,
        "confidence": "low" if reasons else "normal",
        "reasons": reasons,
        "assumes": list(ASSUMES),
    }
