import numpy as np
import astropy.units as u
from astroquery.ipac.ned import Ned
import maglimit.limiting_mag as ml

def test_lim_mag():
    telescope = ml.Telescope(0, 4.5)
    assert telescope.lim_mag()==-inf, "Check aperture, it cannot be zero"

def test_is_object_observable():
    pass

