import math

import pytest

from maglimit.visibility import (
    sky_luminance,
    star_limit,
    surface_brightness,
    verdict,
    visibility_margin,
)

HERSCHEL = {"sqm": 21.83, "eye_pupil": 5.08, "throughput": 1/1.6, "field_factor": 2.36}
BOWEN = {"sqm": 21.27, "eye_pupil": 5.2, "throughput": 0.81, "field_factor": 2.74}


def test_sky_luminance_matches_paper():
    """Test the sky brightness conversion against Crumey's value for SQM 21.83.
    """
    assert sky_luminance(21.83) == pytest.approx(2.0e-4, rel=0.01)


def test_surface_brightness_of_m31():
    """Test the mean surface brightness of M31 from its catalogue values.
    """
    assert surface_brightness(4.29, 177.83, 69.66) == pytest.approx(23.15, abs=0.01)


def test_herschel_star_limits():
    """Test Herschel's star limits at two magnifications, from the paper.
    """
    assert star_limit(475, 157, **HERSCHEL) == pytest.approx(15.66, abs=0.02)
    assert star_limit(475, 328, **HERSCHEL) == pytest.approx(16.39, abs=0.02)


def test_bowen_six_inch_limits():
    """Test Bowen's measured limits for a 6-inch telescope.
    """
    assert star_limit(152, 152/2.5, **BOWEN) == pytest.approx(13.11, abs=0.05)
    assert star_limit(152, 3000, **BOWEN) == pytest.approx(13.96, abs=0.05)


def test_figure_13_cut_off():
    """Test the cut-off limit for a 100 mm telescope in the paper's Figure 13.
    """
    assert star_limit(100, 400, 20, throughput=1/1.3325) == pytest.approx(12.7, abs=0.05)


def test_star_limit_levels_off_at_high_power():
    """Test that the star limit stops improving once the background is below the cut-off.
    """
    limits = [star_limit(200, m, 22) for m in (200, 400, 1000)]
    assert limits[1] == pytest.approx(limits[2], abs=0.01)
    assert limits[0] <= limits[1] + 0.01


def test_herschel_threshold_curve():
    """Test that objects on Herschel's threshold curve (Eq. 89) have a margin of zero.
    """
    for area in (1, 10, 100):
        mu = 23.18 - 4.167*math.log10(0.468*area**-0.6 + 1)
        assert visibility_margin(mu, area, 475, 157, **HERSCHEL) == pytest.approx(0, abs=0.02)


def test_margin_at_very_dark_eyepiece_background_stays_finite():
    """Test a very high magnification under a dark sky.
    """
    assert math.isfinite(visibility_margin(22, 10, 200, 2000, 22))


def test_extended_object_loses_to_brighter_sky():
    """Test that a brighter sky lowers the margin of an extended object.
    """
    margins = [visibility_margin(21, 20, 200, 50, q) for q in (18, 20, 22)]
    assert margins == sorted(margins)


@pytest.mark.parametrize("margin, expected", [
    (2.0, "easy"), (1.99, "moderate"), (1.0, "moderate"), (0.99, "challenging"),
    (0.5, "challenging"), (0.49, "very hard"), (0.0, "very hard"), (-0.01, "not visible"),
])
def test_verdict_bands(margin, expected):
    """Test the verdict for margins on each side of the band edges.
    """
    assert verdict(margin) == expected
