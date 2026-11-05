import pytest

from maglimit.site import Site
from maglimit.telescope import Eyepiece, Telescope


def test_eyepieces_accept_numbers_and_objects():
    """Test that eyepieces can be given as focal lengths or Eyepiece objects.
    """
    scope = Telescope(200, 5, eyepieces=[32, Eyepiece(10, afov=68)])
    assert scope.eyepieces == (Eyepiece(32, 52.0), Eyepiece(10, 68))


def test_defaults():
    """Test the default optional telescope values.
    """
    scope = Telescope(200, 5)
    assert scope.eyepieces == ()
    assert scope.obstruction == 0.0
    assert scope.transmission == 0.8


@pytest.mark.parametrize("kwargs", [
    {"aperture": float("nan"), "fstop": 5},
    {"aperture": float("inf"), "fstop": 5},
    {"aperture": 200, "fstop": float("nan")},
    {"aperture": 200, "fstop": 5, "obstruction": 1.0},
    {"aperture": 200, "fstop": 5, "obstruction": -0.1},
    {"aperture": 200, "fstop": 5, "transmission": 0},
    {"aperture": 200, "fstop": 5, "transmission": 1.1},
])
def test_invalid_telescope_values(kwargs):
    """Test that impossible telescope values are rejected.
    """
    with pytest.raises(ValueError):
        Telescope(**kwargs)


@pytest.mark.parametrize("args", [(0,), (-10,), (float("nan"),), (10, 0), (10, 181)])
def test_invalid_eyepiece(args):
    """Test that impossible eyepiece values are rejected.
    """
    with pytest.raises(ValueError):
        Eyepiece(*args)


def test_v01_import_path_still_works():
    """Test that Telescope is still importable from limiting_mag.
    """
    import maglimit.limiting_mag as ml
    assert ml.Telescope is Telescope


def test_optics_for_200mm_f5():
    """Test optics values for a 200 mm f/5 telescope.
    """
    scope = Telescope(200, 5)
    assert scope.magnification(32) == pytest.approx(31.25)
    assert scope.magnification(Eyepiece(32)) == pytest.approx(31.25)
    assert scope.exit_pupil(32) == pytest.approx(6.4)
    assert scope.exit_pupil(5) == pytest.approx(1.0)
    assert scope.true_field(32) == pytest.approx(1.66)
    assert scope.true_field(Eyepiece(32, afov=68)) == pytest.approx(2.18)
    assert scope.min_magnification() == pytest.approx(28.57)
    assert scope.min_magnification(eye_pupil=5) == pytest.approx(40)
    assert scope.max_magnification() == pytest.approx(400)
    assert scope.dawes_limit() == pytest.approx(0.58)


@pytest.mark.parametrize("value", [0, -5])
def test_magnification_rejects_bad_eyepiece(value):
    """Test that a non-positive eyepiece focal length is rejected.
    """
    with pytest.raises(ValueError):
        Telescope(200, 5).magnification(value)


def test_sky_limit_values():
    """Test the sky-aware star limit under dark and bright skies.
    """
    scope = Telescope(200, 5)
    assert scope.sky_lim_mag(Site(sqm=22)) == pytest.approx(13.77)
    assert scope.sky_lim_mag(Site(sqm=18)) == pytest.approx(11.21)
    assert scope.sky_lim_mag(Site(sqm=22), eyepiece=10) == pytest.approx(14.55)
    assert scope.sky_lim_mag(Site(sqm=18), eyepiece=5) == pytest.approx(13.86)
    assert scope.sky_lim_mag(Site(sqm=20), eyepiece=16) == pytest.approx(13.64)
    assert Telescope(100, 5).sky_lim_mag(Site(sqm=22)) == pytest.approx(12.26)


def test_obstruction_costs_light():
    """Test that a central obstruction lowers the star limit.
    """
    scope = Telescope(200, 5, obstruction=0.3)
    assert scope.sky_lim_mag(Site(sqm=20)) == pytest.approx(12.66)


def test_exit_pupil_larger_than_eye_lowers_the_limit():
    """Test that light beyond the eye's pupil is not counted.
    """
    scope, site = Telescope(200, 5), Site(sqm=20)
    assert scope.sky_lim_mag(site, eyepiece=40) < scope.sky_lim_mag(site, eyepiece=35)


def test_tiny_aperture_stays_sensible():
    """Test an aperture smaller than the eye's pupil.
    """
    assert Telescope(5, 5).sky_lim_mag(Site(sqm=22)) == pytest.approx(5.76)


def test_more_aperture_never_hurts():
    """Test that the star limit improves with aperture.
    """
    site = Site(sqm=20)
    limits = [Telescope(d, 5).sky_lim_mag(site, eyepiece=10) for d in (50, 100, 200, 400)]
    assert limits == sorted(limits)


def test_darker_sky_never_hurts():
    """Test that the star limit improves as the sky gets darker.
    """
    scope = Telescope(200, 5)
    limits = [scope.sky_lim_mag(Site(bortle=b), eyepiece=10) for b in range(9, 0, -1)]
    assert limits == sorted(limits)


def test_lim_mag_is_unchanged():
    """Test that lim_mag() still depends only on the aperture.
    """
    assert Telescope(200, 5, obstruction=0.3).lim_mag() == pytest.approx(13.51)
