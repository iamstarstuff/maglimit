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
