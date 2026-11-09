"""Answers "can I see this object with this telescope under this sky?"
"""
import functools
import math
import os
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import astropy.units as u
import numpy as np
from astropy.table import QTable

from .catalogue import find_object, load_catalogue
from .ephemeris import altitudes, night, separations, tonight_date
from .telescope import _check_eye_pupil
from .visibility import (
    extinction,
    moon_sky_brightness,
    star_limit,
    surface_brightness,
    used_aperture,
    verdict,
    visibility_margin,
)

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
# Friendly names for groups of OpenNGC types, for tonight(types=...)
TYPE_GROUPS = {
    "galaxy": {"G", "GPair", "GTrpl", "GGroup"},
    "globular": {"GCl"},
    "open": {"OCl", "*Ass"},
    "nebula": {"HII", "Neb", "EmN", "RfN", "SNR", "Cl+N"},
    "pn": {"PN"},
}
# Types the model can't judge, never listed by tonight()
NEVER_LISTED = {"DrkN"}
GOALS = ("easy", "challenge")
# goal="easy" ranks by verdict band, then Messier objects first, then brightest first,
# with each degree above the minimum altitude counting as this many magnitudes brighter.
# Raw margins aren't used directly: they reach 5-7 for tiny bright objects, which would
# put small planetaries ahead of M31 and M42.
ALTITUDE_WEIGHT = 0.01
BANDS = ("easy", "moderate", "challenging", "very hard", "not visible")
# The Moon counts against confidence once it brightens the sky by this many magnitudes
MOON_REASON_MAG = 0.5
MOON_REASON = "the Moon brightens the sky (simple estimate)"


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


def _margins(obj, telescope, sqm, magnification, eye_pupil, field_factor, dimming=0.0):
    """Returns (margin, seen_as) pairs for one magnification, with the object dimmed
    by dimming magnitudes
    """
    aperture = used_aperture(telescope._aperture_mm(), magnification, eye_pupil)
    model = {"sqm": sqm, "eye_pupil": MODEL_PUPIL, "throughput": telescope.throughput(),
                 "field_factor": field_factor}
    if "no_size" in obj.flags:
        return [(star_limit(aperture, magnification, **model) - obj.magnitude - dimming,
                 "point source")]
    area = math.pi/4*obj.major_axis*obj.minor_axis
    mu = surface_brightness(obj.magnitude, obj.major_axis, obj.minor_axis) + dimming
    margins = [(visibility_margin(mu, area, aperture, magnification, **model), "whole object")]
    if obj.type in CORE_TYPES:
        core_mu = mu - 2.5*math.log10(CORE_LIGHT/CORE_AREA)
        margins.append((visibility_margin(core_mu, area*CORE_AREA, aperture, magnification,
                                          **model), "bright core"))
    return margins


def _assess(obj, telescope, sqm, eye_pupil, field_factor, dimming=0.0):
    """Finds the best way to see an object

    Returns:
        (margin, seen_as, magnification, eyepiece focal length or None), unrounded
    """
    best = None
    for magnification, eyepiece in _candidates(telescope, eye_pupil):
        for margin, seen_as in _margins(obj, telescope, sqm, magnification, eye_pupil,
                                        field_factor, dimming):
            if best is None or margin > best[0]:
                best = (margin, seen_as, magnification, eyepiece)
    return best


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
    margin, seen_as, magnification, eyepiece = _assess(obj, telescope, sqm, eye_pupil,
                                                       field_factor)
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


@functools.cache
def _listable():
    """Returns the objects tonight() can list, with their coordinates as arrays
    """
    objects = tuple(o for o in load_catalogue()
                    if o.magnitude is not None and o.type not in NEVER_LISTED)
    return objects, np.array([o.ra for o in objects]), np.array([o.dec for o in objects])


def _system_zone():
    """Returns the system's time zone, by IANA name where it can be found

    Tries the TZ variable, then the /etc/localtime link, so daylight saving is
    followed; falls back to the current fixed UTC offset.
    """
    candidates = [os.environ.get("TZ", "").lstrip(":")]
    try:
        link = str(Path("/etc/localtime").resolve())
        candidates.append(link.split("zoneinfo/", 1)[1] if "zoneinfo/" in link else "")
    except OSError:
        pass
    for key in candidates:
        if key:
            try:
                return ZoneInfo(key)
            except (ZoneInfoNotFoundError, ValueError):
                continue
    return datetime.now().astimezone().tzinfo


def _zone(tz):
    """Returns a tzinfo for an IANA name, a tzinfo, or None for the system's zone
    """
    if tz is None:
        return _system_zone()
    return ZoneInfo(tz) if isinstance(tz, str) else tz


def _now(zone):
    """Returns the current time in a zone
    """
    return datetime.now(zone)


def _night_date(date, zone):
    """Returns the date a plan is for, from None, a date or an ISO string
    """
    if date is None:
        return tonight_date(_now(zone))
    if isinstance(date, date_type):
        return date
    try:
        return date_type.fromisoformat(date)
    except (TypeError, ValueError):
        raise ValueError(f"date must be a date or YYYY-MM-DD, got {date!r}") from None


def _allowed_types(types):
    """Returns the set of OpenNGC types to keep, or None for all
    """
    if types is None:
        return None
    unknown = [t for t in types if t not in TYPE_GROUPS]
    if unknown:
        raise ValueError(f"unknown type group {', '.join(unknown)}; "
                         f"choose from {', '.join(TYPE_GROUPS)}")
    return set().union(*(TYPE_GROUPS[t] for t in types))


def _nan(value):
    """Returns value, or NaN for None
    """
    return math.nan if value is None else value


def tonight(telescope, site, date=None, tz=None, types=None, goal="easy", limit=20,
            min_altitude=20.0, sun_altitude=-18.0, show_hidden=False, eye_pupil=7.0,
            field_factor=2.0):
    """Ranks the objects worth looking at tonight

    Each object is judged at its highest point in the dark, and at its highest point
    while the Moon is down, and the better view wins. The atmosphere dims low objects
    (relative to the zenith), and a Moon above the horizon brightens the sky.

    Args:
        telescope: Telescope used
        site: Site with lat, lon and sky darkness
        date: local date the night starts on, as a date or "YYYY-MM-DD"; default tonight,
            which before noon means the night still running
        tz: time zone, an IANA name such as "Asia/Kolkata" or a tzinfo; default the system's
        types: type groups to keep, from TYPE_GROUPS; default all
        goal: "easy" for the easiest first, "challenge" for the hardest still visible first
        limit: number of visible objects to list
        min_altitude: lowest useful altitude in degrees
        sun_altitude: the Sun must be below this altitude in degrees for darkness
        show_hidden: also list objects that are up but below threshold, after the rest
        eye_pupil: diameter of the observer's dark-adapted pupil in mm
        field_factor: Crumey's factor between laboratory and field thresholds

    Returns:
        astropy QTable, one row per object, with the night described in its meta

    Raises:
        ValueError: if an option is invalid, the site has no location, or there is no
            darkness on that date
    """
    _check_eye_pupil(eye_pupil)
    if goal not in GOALS:
        raise ValueError(f"goal must be easy or challenge, got {goal!r}")
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")
    allowed = _allowed_types(types)
    zone = _zone(tz)
    day = _night_date(date, zone)
    dark = night(site, day, zone, sun_altitude=sun_altitude)
    if date is None:
        dark = dark.after(_now(zone))
        if dark is None:
            raise ValueError(f"darkness has ended for the night of {day.isoformat()}; "
                             "give a date to plan another night")

    objects, ra, dec = _listable()
    keep = np.array([allowed is None or o.type in allowed for o in objects])
    alt = altitudes(ra, dec, site.lat, dark.lst)
    moon_down = dark.moon_altitude <= 0
    candidates = [alt.argmax(axis=1)]
    if moon_down.any():
        candidates.append(np.where(moon_down, alt, -np.inf).argmax(axis=1))
    rows_index = np.arange(len(objects))
    up = keep & (alt.max(axis=1) >= min_altitude)
    sqm = float(site.sqm)

    results = []
    for i in rows_index[up]:
        obj = objects[i]
        best = None
        for sample in {int(c[i]) for c in candidates}:
            altitude = float(alt[i, sample])
            if altitude < min_altitude:
                continue
            moon_alt = float(dark.moon_altitude[sample])
            separation = float(separations(obj.ra, obj.dec, dark.moon_ra[sample],
                                           dark.moon_dec[sample]))
            sky = moon_sky_brightness(sqm, float(dark.moon_illumination[sample]), separation,
                                      moon_alt)
            assessed = _assess(obj, telescope, sky, eye_pupil, field_factor,
                               extinction(altitude))
            if best is None or assessed[0] > best[0][0]:
                best = (assessed, sample, altitude, sky, separation if moon_alt > 0 else None)
        # Round before splitting visible from hidden, as verdicts are graded on the
        # rounded margin; adding 0.0 turns -0.0 into 0.0
        assessed, *rest = best
        results.append((obj, (round(assessed[0], 2) + 0.0, *assessed[1:]), *rest))

    def score(result):
        obj, (margin, *_), _, altitude, *_ = result
        if goal == "challenge":
            return (margin, -altitude)
        return (BANDS.index(verdict(round(margin, 2))), obj.messier is None,
                obj.magnitude - ALTITUDE_WEIGHT*(altitude - min_altitude))

    visible = sorted((r for r in results if r[1][0] >= 0), key=score)
    hidden = sorted((r for r in results if r[1][0] < 0), key=lambda r: -r[1][0])
    listed = visible[:limit] + (hidden[:limit] if show_hidden else [])

    rows = []
    for obj, (margin, seen_as, magnification, eyepiece), sample, altitude, sky, moon_sep in listed:
        reasons = _reasons(obj, sky)
        if sqm - sky >= MOON_REASON_MAG:
            reasons.append(MOON_REASON)
        margin = round(margin, 2)
        rows.append({
            "name": f"M{obj.messier}" if obj.messier is not None else obj.name,
            "catalogue_name": obj.name,
            "type": obj.type,
            "magnitude": obj.magnitude,
            "major_axis": _nan(obj.major_axis),
            "minor_axis": _nan(obj.minor_axis),
            "sample": sample,
            "altitude": round(altitude, 2),
            "magnification": round(magnification, 2),
            "eyepiece": _nan(eyepiece),
            "margin": margin,
            "verdict": verdict(margin),
            "seen_as": seen_as,
            "moon_separation": round(_nan(moon_sep), 2),
            "confidence": "low" if reasons else "normal",
            "reasons": "; ".join(reasons),
        })

    def column(key, dtype=None):
        return np.array([row[key] for row in rows], dtype=dtype)

    table = QTable()
    for key in ("name", "catalogue_name", "type"):
        table[key] = column(key, str)
    for key in ("magnitude", "major_axis", "minor_axis"):
        table[key] = column(key, float)
    table["best_time"] = dark.times[column("sample", int)]
    table["altitude"] = column("altitude", float)*u.deg
    for key in ("magnification", "eyepiece", "margin"):
        table[key] = column(key, float)
    for key in ("verdict", "seen_as"):
        table[key] = column(key, str)
    table["moon_separation"] = column("moon_separation", float)*u.deg
    for key in ("confidence", "reasons"):
        table[key] = column(key, str)
    table.meta.update({
        "date": day.isoformat(),
        "tz": str(zone),
        "dark_start": dark.dark_start,
        "dark_end": dark.dark_end,
        "sky_sqm": sqm,
        "moon_illumination": round(float(dark.moon_illumination[len(dark.times)//2]), 2),
        "star_limit": telescope.sky_lim_mag(site, eye_pupil=eye_pupil),
        "goal": goal,
        "hidden": len(hidden),
    })
    return table
