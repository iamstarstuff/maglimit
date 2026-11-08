"""When it's dark, where objects are, and what the Moon is doing.

astropy gives the Sun, the Moon and the sidereal time once per sample. Object
altitudes are plain numpy over the whole catalogue, using its J2000
coordinates without precession (about 0.2 degrees off in the 2020s), so the
same formulas port to other languages.
"""
import contextlib
import warnings
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, EarthLocation, get_body
from astropy.time import Time
from astropy.utils import iers
from erfa import ErfaWarning


@contextlib.contextmanager
def offline_iers():
    """Stops astropy from downloading Earth-orientation data, for the duration only

    Minute-level accuracy is plenty for planning, and this keeps maglimit offline
    without changing the user's own astropy settings. Future dates also get
    ERFA's "dubious year" warning, as leap seconds aren't known that far ahead,
    and astropy's arcsecond-level polar-motion warning; neither matters at this
    accuracy, so both are silenced here too.
    """
    with iers.conf.set_temp("auto_download", False), \
            iers.conf.set_temp("auto_max_age", None), \
            iers.conf.set_temp("iers_degraded_accuracy", "ignore"), \
            warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ErfaWarning, message=".*dubious year")
        warnings.filterwarnings("ignore", message="Tried to get polar motions")
        yield


def tonight_date(now):
    """Returns the local date the current or coming night starts on

    Args:
        now: local date and time

    Returns:
        The date of now, or the day before when it's earlier than noon
    """
    if now.hour < 12:
        return now.date() - timedelta(days=1)
    return now.date()


def altitudes(ra, dec, lat, lst):
    """Calculates the altitudes of objects at a set of sidereal times

    Args:
        ra: right ascensions in degrees, array
        dec: declinations in degrees, array
        lat: latitude of the site in degrees
        lst: local sidereal times in degrees, array

    Returns:
        Altitudes in degrees, shape (objects, times)
    """
    ra, dec, lst = (np.radians(np.asarray(x, dtype=float)) for x in (ra, dec, lst))
    lat = np.radians(lat)
    hour_angle = lst[None, :] - ra[:, None]
    sin_alt = (np.sin(lat)*np.sin(dec)[:, None]
               + np.cos(lat)*np.cos(dec)[:, None]*np.cos(hour_angle))
    return np.degrees(np.arcsin(np.clip(sin_alt, -1, 1)))


def separations(ra1, dec1, ra2, dec2):
    """Calculates angular separations, broadcasting like numpy

    Args:
        ra1, dec1, ra2, dec2: coordinates in degrees

    Returns:
        Separations in degrees
    """
    ra1, dec1, ra2, dec2 = (np.radians(np.asarray(x, dtype=float)) for x in (ra1, dec1, ra2, dec2))
    half = (np.sin((dec2 - dec1)/2)**2
            + np.cos(dec1)*np.cos(dec2)*np.sin((ra2 - ra1)/2)**2)
    return np.degrees(2*np.arcsin(np.sqrt(np.clip(half, 0, 1))))


@dataclass(frozen=True)
class Night:
    """The dark part of one night, sampled at regular times.

    Args:
        times: astropy Time of each dark sample
        dark_start: when darkness starts, aware datetime in tz
        dark_end: when darkness ends, aware datetime in tz
        lst: local sidereal time of each sample in degrees
        moon_ra: right ascension of the Moon at each sample in degrees
        moon_dec: declination of the Moon at each sample in degrees
        moon_altitude: altitude of the Moon at each sample in degrees
        moon_illumination: illuminated fraction of the Moon at each sample
        tz: time zone the night is described in
    """
    times: Time
    dark_start: datetime
    dark_end: datetime
    lst: np.ndarray
    moon_ra: np.ndarray
    moon_dec: np.ndarray
    moon_altitude: np.ndarray
    moon_illumination: np.ndarray
    tz: object


def _crossing(times, sun, before, after, sun_altitude):
    """Interpolates when the Sun crosses sun_altitude between two samples
    """
    fraction = (sun[before] - sun_altitude)/(sun[before] - sun[after])
    return times[before] + fraction*(times[after] - times[before])


def night(site, date, tz, sun_altitude=-18.0, step_minutes=10):
    """Samples the dark part of the night starting on a local date

    Samples run from local noon on date to noon the next day.

    Args:
        site: Site with lat and lon
        date: local date the night starts on
        tz: time zone, a tzinfo
        sun_altitude: the Sun must be below this altitude in degrees for darkness
        step_minutes: minutes between samples

    Returns:
        Night

    Raises:
        ValueError: if the site has no location, or the Sun never gets low enough
    """
    if site.lat is None or site.lon is None:
        raise ValueError("the site needs lat and lon to plan a night")
    with offline_iers():
        noon = datetime.combine(date, time(12), tzinfo=tz).astimezone(timezone.utc)
        steps = 24*60//step_minutes
        times = Time([noon + timedelta(minutes=step_minutes*i) for i in range(steps + 1)])
        location = EarthLocation(lat=site.lat*u.deg, lon=site.lon*u.deg,
                                 height=(site.elevation or 0.0)*u.m)
        frame = AltAz(obstime=times, location=location)
        sun_body = get_body("sun", times, location)
        sun = sun_body.transform_to(frame).alt.deg
        dark = np.flatnonzero(sun < sun_altitude)
        if len(dark) == 0:
            raise ValueError(
                f"no astronomical darkness on {date.isoformat()} at latitude {site.lat:g}; "
                f"try sun_altitude=-12")
        moon_body = get_body("moon", times, location)
        moon_altitude = moon_body.transform_to(frame).alt.deg
        elongation = sun_body.separation(moon_body).deg
        lst = times.sidereal_time("mean", longitude=site.lon*u.deg).deg
        first, last = dark[0], dark[-1]
        start = times[first] if first == 0 else _crossing(times, sun, first - 1, first, sun_altitude)
        end = times[last] if last == steps else _crossing(times, sun, last + 1, last, sun_altitude)
        return Night(
            times=times[dark],
            dark_start=start.to_datetime(timezone=tz),
            dark_end=end.to_datetime(timezone=tz),
            lst=np.asarray(lst)[dark],
            moon_ra=np.asarray(moon_body.ra.deg)[dark],
            moon_dec=np.asarray(moon_body.dec.deg)[dark],
            moon_altitude=np.asarray(moon_altitude)[dark],
            moon_illumination=((1 - np.cos(np.radians(elongation)))/2)[dark],
            tz=tz,
        )
