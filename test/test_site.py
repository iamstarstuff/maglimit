import pytest

from maglimit.site import Site, bortle_to_sqm, naked_eye_limit


def test_naked_eye_limit():
    """Test the naked-eye limit under a dark and a bright sky.
    """
    assert naked_eye_limit(22) == pytest.approx(6.62, abs=0.01)
    assert naked_eye_limit(18) == pytest.approx(3.97, abs=0.02)


def test_bortle_lookup():
    """Test typical SQM values for Bortle classes.
    """
    assert bortle_to_sqm(1) == 22.0
    assert bortle_to_sqm(5) == 20.0
    assert bortle_to_sqm(9) == 17.5


def test_darker_bortle_gives_a_better_limit():
    """Test that the naked-eye limit improves as the sky gets darker.
    """
    limits = [Site(bortle=b).nelm for b in range(9, 0, -1)]
    assert limits == sorted(limits)


def test_site_from_bortle_or_sqm():
    """Test that sky brightness can be given either way.
    """
    assert Site(bortle=5).sqm == 20.0
    assert Site(sqm=20.1).sqm == 20.1
    assert Site(bortle=5).nelm == pytest.approx(5.49)


def test_sqm_wins_over_bortle():
    """Test that a measured SQM takes priority over a Bortle class.
    """
    assert Site(bortle=9, sqm=21.5).sqm == 21.5


def test_location_is_optional():
    """Test that a site can be given with or without a location.
    """
    site = Site(lat=18.5, lon=73.9, bortle=5)
    assert (site.lat, site.lon, site.elevation) == (18.5, 73.9, 0.0)
    assert Site(bortle=5).lat is None


@pytest.mark.parametrize("kwargs", [
    {},
    {"bortle": 0}, {"bortle": 10}, {"bortle": 4.5}, {"bortle": True},
    {"sqm": 200}, {"sqm": 10}, {"sqm": float("nan")},
    {"bortle": 5, "lat": 95}, {"bortle": 5, "lon": 200},
    {"bortle": 5, "lat": float("nan")},
    {"bortle": 12, "sqm": 20},
])
def test_invalid_site(kwargs):
    """Test that missing or impossible site values are rejected.
    """
    with pytest.raises(ValueError):
        Site(**kwargs)
