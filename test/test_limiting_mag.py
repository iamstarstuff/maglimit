import astropy.units as u
import pytest

import maglimit.limiting_mag as ml


@pytest.fixture
def fake_ned(monkeypatch):
    """Replaces the NED query with a lookup table, so tests run offline.
    """
    magnitudes = {"M31": 4.36, "NGC 244": 13.83, "NOMAG": None}

    def query_object(obj):
        return {"Magnitude and Filter": [magnitudes[obj]]}

    monkeypatch.setattr(ml.Ned, "query_object", query_object)


@pytest.mark.parametrize("aperture, fstop", [(0, 4.5), (-100, 4.5), (100, 0)])
def test_invalid_telescope(aperture, fstop):
    """Test that non-positive aperture or fstop is rejected.
    """
    with pytest.raises(ValueError):
        ml.Telescope(aperture, fstop)


def test_lim_mag():
    """Test to check the correctness of lim_mag() function.
    """
    assert ml.Telescope(100, 4.5).lim_mag() == pytest.approx(12.0)
    assert ml.Telescope(200, 5).lim_mag() == pytest.approx(13.51)


def test_focal_length():
    """Test to check the correctness of the focal_length() function
    """
    focal_length = ml.Telescope(100, 4.5).focal_length()
    assert focal_length.unit == u.mm
    assert focal_length.value == pytest.approx(450, abs=1e-4)


def test_magnification():
    """Test to check the correctness of the magnification() function
    """
    telescope = ml.Telescope(100, 4.5)
    assert telescope.magnification(10) == pytest.approx(45)
    assert telescope.magnification(32) == pytest.approx(14.06)


def test_is_object_observable(fake_ned):
    """Test bright and faint objects against a 100mm scope.
    """
    lm = ml.Telescope(100, 4.5).lim_mag()
    assert ml.is_object_observable("M31", lm) is True
    assert ml.is_object_observable("NGC 244", lm) is False


def test_smallest_scope(fake_ned):
    """Test the minimum aperture and focal length for NGC 244.
    """
    ob, ap, fl = ml.smallest_scope("NGC 244", fs=4.5)
    assert ob == pytest.approx(13.83)
    assert ap.to_value(u.mm) == pytest.approx(232.27)
    assert fl.to_value(u.mm) == pytest.approx(1045.22)


def test_missing_magnitude(fake_ned):
    """Test that an object without a NED magnitude gives a clear error.
    """
    with pytest.raises(ValueError, match="no magnitude"):
        ml.object_magnitude("NOMAG")


@pytest.mark.network
def test_live_ned_query():
    """Test a real NED query for M31.
    """
    assert ml.object_magnitude("M31") == pytest.approx(4.36, abs=0.5)
