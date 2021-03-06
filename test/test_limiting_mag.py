import pytest
import numpy as np
import astropy.units as u
from astroquery.ipac.ned import Ned
import maglimit.limiting_mag as ml

def test_lim_mag():
    """Test to check the correctness of lim_mag() function.
    """
    telescope = ml.Telescope(0, 4.5)
    assert telescope.lim_mag()==-np.inf, "Check aperture, it cannot be zero"


def test_focal_length():
    """Test to check the correctness of the focal_length() function
    """
    aperture = 100
    fstop = 4.5
    foc_len_exp = aperture*fstop

    telescope = ml.Telescope(100,4.5)
    focal_length = telescope.focal_length().value
    assert focal_length == pytest.approx(foc_len_exp, abs=1e-4)


def test_magnification():
    """Test to check the correctness of the magnification() function
    """
    foc_len = 450
    f_eyepiece = 10
    mag_exp = foc_len/f_eyepiece

    telescope = ml.Telescope(100, 4.5)
    focal_length = telescope.focal_length()
    mag = telescope.magnification(10)
    assert mag == pytest.approx(mag_exp)


