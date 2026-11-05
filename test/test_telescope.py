import pytest

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
