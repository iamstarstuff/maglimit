import math

import pytest

from maglimit.visibility import (
    airmass,
    extinction,
    moon_sky_brightness,
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


def test_airmass_kasten_young():
    """Test airmass against Kasten and Young (1989) values.
    """
    assert airmass(90) == pytest.approx(1.0, abs=1e-3)
    assert airmass(30) == pytest.approx(1.9943, abs=1e-3)
    assert airmass(20) == pytest.approx(2.9031, abs=1e-3)


def test_airmass_rejects_objects_below_horizon():
    """Test that airmass refuses an altitude at or below the horizon.
    """
    with pytest.raises(ValueError):
        airmass(0)


def test_extinction_is_relative_to_zenith():
    """Test that extinction is zero overhead and 0.476 mag at 20 degrees.
    """
    assert extinction(90) == 0.0
    assert extinction(20) == pytest.approx(0.476, abs=1e-3)


def test_lower_never_dims_less():
    """Test that a lower object is never dimmed less than a higher one.
    """
    values = [extinction(a) for a in range(5, 91)]
    assert values == sorted(values, reverse=True)


@pytest.mark.parametrize(("illumination", "separation", "expected"),
                         [(1.0, 90, 19.794), (1.0, 30, 18.602), (0.1, 60, 21.012)])
def test_moon_sky_brightness(illumination, separation, expected):
    """Test the moonlit sky over a Bortle 3 site against hand-worked values.
    """
    sky = moon_sky_brightness(21.7, illumination, separation, 40)
    assert sky == pytest.approx(expected, abs=1e-3)


def test_moon_below_horizon_leaves_sky_alone():
    """Test that a set Moon or a new Moon doesn't change the sky.
    """
    assert moon_sky_brightness(21.7, 1.0, 30, -5) == 21.7
    assert moon_sky_brightness(21.7, 0.0, 30, 40) == 21.7


def test_brighter_or_closer_moon_never_darkens_sky():
    """Test that more illumination or a smaller separation never darkens the sky.
    """
    by_phase = [moon_sky_brightness(20.0, k/10, 45, 30) for k in range(1, 11)]
    by_distance = [moon_sky_brightness(20.0, 0.8, s, 30) for s in range(0, 181, 10)]
    assert by_phase == sorted(by_phase, reverse=True)
    assert by_distance == sorted(by_distance)
