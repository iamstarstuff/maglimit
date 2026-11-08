from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from maglimit.catalogue import find_object
from maglimit.ephemeris import altitudes, night, separations, tonight_date
from maglimit.site import Site

PUNE = Site(lat=18.5, lon=73.9, bortle=5)
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
LONDON = Site(lat=51.48, lon=0.0, bortle=5)


def test_tonight_date_in_the_evening():
    """Test that an evening time plans the night starting that day.
    """
    assert tonight_date(datetime(2026, 11, 1, 20, 0)) == date(2026, 11, 1)


def test_tonight_date_after_midnight():
    """Test that a time after midnight plans the night still running.
    """
    assert tonight_date(datetime(2026, 11, 2, 2, 0)) == date(2026, 11, 1)


def test_altitude_of_pole_star_is_latitude():
    """Test that an object at the celestial pole sits at the site's latitude.
    """
    alt = altitudes(np.array([0.0]), np.array([90.0]), 18.5, np.array([0.0, 90.0, 180.0]))
    assert alt == pytest.approx(np.full((1, 3), 18.5))


def test_separation_quarter_circle():
    """Test the separation of a point on the equator and the pole.
    """
    assert separations(10.0, 0.0, 200.0, 90.0) == pytest.approx(90.0)


def test_pune_darkness_window():
    """Test the darkness window at Pune on 2026-11-01 against a 1-minute astropy run.
    """
    n = night(PUNE, date(2026, 11, 1), KOLKATA_TZ)
    start = datetime(2026, 11, 1, 19, 16, tzinfo=KOLKATA_TZ)
    end = datetime(2026, 11, 2, 5, 20, tzinfo=KOLKATA_TZ)
    assert abs(n.dark_start - start) < timedelta(minutes=3)
    assert abs(n.dark_end - end) < timedelta(minutes=3)


def test_m31_highest_altitude_at_pune():
    """Test M31's highest altitude on the Pune night against astropy's 67.06 degrees.
    """
    n = night(PUNE, date(2026, 11, 1), KOLKATA_TZ)
    m31 = find_object("M31")
    alt = altitudes(np.array([m31.ra]), np.array([m31.dec]), 18.5, n.lst)
    assert alt.max() == pytest.approx(67.06, abs=0.5)


@pytest.mark.parametrize(("site", "day", "zone", "expected"), [
    (LONDON, date(2026, 12, 21), "Europe/London", 0.93),
    (Site(lat=-33.9, lon=18.4, bortle=5), date(2026, 3, 15), "Africa/Johannesburg", 0.11),
])
def test_moon_illumination(site, day, zone, expected):
    """Test the Moon's illuminated fraction near local midnight against astropy runs.
    """
    n = night(site, day, ZoneInfo(zone))
    assert n.moon_illumination[len(n.times)//2] == pytest.approx(expected, abs=0.03)


def test_no_darkness_in_london_midsummer():
    """Test that a night with no astronomical darkness is a clear error.
    """
    with pytest.raises(ValueError, match="sun_altitude=-12"):
        night(LONDON, date(2026, 6, 21), ZoneInfo("Europe/London"))


def test_shallower_sun_altitude_gives_a_window():
    """Test that nautical darkness exists in London at midsummer.
    """
    n = night(LONDON, date(2026, 6, 21), ZoneInfo("Europe/London"), sun_altitude=-12)
    assert len(n.times) > 0


def test_night_needs_a_location():
    """Test that a site without latitude and longitude is refused.
    """
    with pytest.raises(ValueError, match="lat"):
        night(Site(bortle=5), date(2026, 11, 1), KOLKATA_TZ)


def test_night_never_downloads(monkeypatch):
    """Test that computing a night far in the future never touches the network.
    """
    def refuse(*args, **kwargs):
        raise AssertionError("tried to download")
    monkeypatch.setattr("astropy.utils.data.download_file", refuse)
    monkeypatch.setattr("astropy.utils.iers.IERS_Auto.iers_table", None)
    night(PUNE, date(2031, 1, 10), KOLKATA_TZ)
