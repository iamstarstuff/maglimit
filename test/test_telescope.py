import json

import numpy as np
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
    assert scope.sky_lim_mag(Site(sqm=22)) == pytest.approx(13.01)
    assert scope.sky_lim_mag(Site(sqm=18)) == pytest.approx(11.63)
    assert scope.sky_lim_mag(Site(sqm=22), eyepiece=10) == pytest.approx(14.21)
    assert scope.sky_lim_mag(Site(sqm=18), eyepiece=5) == pytest.approx(13.11)
    assert scope.sky_lim_mag(Site(sqm=20), eyepiece=16) == pytest.approx(12.89)
    assert Telescope(100, 5).sky_lim_mag(Site(sqm=22)) == pytest.approx(11.51)


def test_obstruction_costs_light():
    """Test that a central obstruction lowers the star limit.
    """
    scope = Telescope(200, 5, obstruction=0.3)
    assert scope.sky_lim_mag(Site(sqm=20)) == pytest.approx(12.17)


def test_exit_pupil_larger_than_eye_lowers_the_limit():
    """Test that light beyond the eye's pupil is not counted.
    """
    scope, site = Telescope(200, 5), Site(sqm=20)
    assert scope.sky_lim_mag(site, eyepiece=40) < scope.sky_lim_mag(site, eyepiece=35)


def test_tiny_aperture_stays_sensible():
    """Test an aperture smaller than the eye's pupil.
    """
    assert Telescope(5, 5).sky_lim_mag(Site(sqm=22)) == pytest.approx(5.0)


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


def test_throughput_includes_obstruction():
    """Test the fraction of light passed by an obstructed telescope.
    """
    assert Telescope(200, 5, obstruction=0.3).throughput() == pytest.approx(0.728)


def test_used_aperture():
    """Test that an exit pupil wider than the eye uses less of the aperture.
    """
    from maglimit.visibility import used_aperture
    assert used_aperture(200, 25, 5) == pytest.approx(125)
    assert used_aperture(200, 100, 5) == pytest.approx(200)


def test_lim_mag_is_unchanged():
    """Test that lim_mag() still depends only on the aperture.
    """
    assert Telescope(200, 5, obstruction=0.3).lim_mag() == pytest.approx(13.51)


def test_summary_is_plain_data():
    """Test that the summary holds the right values and can be saved as JSON.
    """
    summary = Telescope(200, 5, eyepieces=[32, 2]).summary(Site(sqm=20))
    json.dumps(summary)
    assert summary["focal_length_mm"] == 1000
    assert summary["star_limit"] == pytest.approx(13.51)
    assert summary["eyepieces"][0]["exit_pupil_mm"] == pytest.approx(6.4)
    assert summary["eyepieces"][1]["notes"] == ["above max useful magnification"]


def test_summary_flags_large_exit_pupil():
    """Test the note for an exit pupil wider than the eye, with no site given.
    """
    summary = Telescope(200, 5, eyepieces=[40]).summary()
    assert summary["eyepieces"][0]["notes"] == ["exit pupil larger than your eye"]
    assert summary["sky_star_limit"] is None
    assert summary["eyepieces"][0]["sky_star_limit"] is None


@pytest.mark.parametrize("eye_pupil", [0, -1, float("nan"), 0.7, 70])
def test_invalid_eye_pupil(eye_pupil):
    """Test that an impossible eye pupil is rejected.
    """
    scope = Telescope(200, 5)
    with pytest.raises(ValueError):
        scope.min_magnification(eye_pupil)
    with pytest.raises(ValueError):
        scope.sky_lim_mag(Site(sqm=20), eye_pupil=eye_pupil)


def test_eye_pupil_does_not_matter_when_exit_pupil_fits():
    """Test that all the light reaches any eye wider than the exit pupil.
    """
    scope, site = Telescope(200, 5), Site(sqm=20)
    assert [scope.sky_lim_mag(site, 10, p) for p in (3, 5, 7)] == [13.32, 13.32, 13.32]


def test_smaller_eye_pupil_loses_light_from_wide_exit_pupil():
    """Test that a smaller eye gets a lower limit when the exit pupil overfills it.
    """
    scope, site = Telescope(200, 5), Site(sqm=20)
    assert [scope.sky_lim_mag(site, 40, p) for p in (3, 5, 7)] == [10.82, 11.48, 11.94]
    assert [scope.sky_lim_mag(site, 32, p) for p in (3, 5, 7)] == [11.30, 11.97, 12.30]


def test_methods_return_plain_floats():
    """Test that numeric results are plain floats, not numpy types.
    """
    scope, site = Telescope(200, 5), Site(sqm=20)
    results = [
        scope.magnification(25), scope.exit_pupil(25), scope.true_field(25),
        scope.min_magnification(), scope.max_magnification(), scope.dawes_limit(),
        scope.lim_mag(), scope.sky_lim_mag(site), site.nelm,
    ]
    assert [type(result) for result in results] == [float]*len(results)


def test_summary_with_numpy_inputs_is_json_safe():
    """Test that values from a numpy sweep still give a JSON-ready summary.
    """
    scope = Telescope(np.float32(200), np.int64(5), [np.int64(10)])
    json.dumps(scope.summary(Site(sqm=np.float32(20))))


def test_smaller_eye_pupil_never_raises_low_power_limit():
    """Test that with no eyepiece given, a smaller eye never sees fainter stars.
    """
    scope, site = Telescope(200, 5), Site(sqm=21.5)
    limits = [scope.sky_lim_mag(site, eye_pupil=p) for p in (1, 3, 5, 7, 10)]
    assert limits == sorted(limits)
