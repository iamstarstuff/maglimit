import json
from dataclasses import replace

import pytest

from maglimit import planner
from maglimit.catalogue import find_object
from maglimit.planner import explain
from maglimit.site import Site
from maglimit.telescope import Telescope


def test_explain_is_plain_data():
    """Test that explain() gives a JSON-ready answer for M57 with two eyepieces.
    """
    result = explain("M57", Telescope(200, 5, eyepieces=[32, 10]), Site(bortle=5))
    json.dumps(result)
    assert result["verdict"] == "easy"
    assert result["best_eyepiece"] == 10
    assert result["seen_as"] == "whole object"
    assert result["confidence"] == "normal"
    assert "object at the zenith, no Moon" in result["assumes"]


def test_galaxy_is_seen_by_its_core():
    """Test that M31 under a city sky is seen by its bright core.
    """
    assert explain("M31", Telescope(200, 5), Site(bortle=8))["seen_as"] == "bright core"


def test_nebula_has_low_confidence():
    """Test that an emission nebula gets a low-confidence answer with reasons.
    """
    result = explain("NGC 7000", Telescope(200, 5), Site(bortle=5))
    assert result["confidence"] == "low"
    assert result["reasons"]


def test_bright_sky_has_low_confidence():
    """Test that a sky brighter than SQM 19 lowers confidence.
    """
    assert explain("M13", Telescope(200, 5), Site(bortle=8))["confidence"] == "low"


def test_object_without_size_is_a_point_source():
    """Test that an object with no size is treated as a point source.
    """
    result = explain("M40", Telescope(200, 5), Site(bortle=5))
    assert result["seen_as"] == "point source"
    assert result["confidence"] == "low"


def test_object_without_magnitude_gives_clear_error(monkeypatch):
    """Test that an object with no magnitude gives a clear error.
    """
    fake = replace(find_object("M13"), magnitude=None)
    monkeypatch.setattr(planner, "find_object", lambda name: fake)
    with pytest.raises(ValueError, match="no magnitude"):
        explain("M13", Telescope(200, 5), Site(bortle=5))


def test_more_aperture_never_hurts_visibility():
    """Test that a bigger telescope never lowers the margin.
    """
    margins = [explain("M51", Telescope(d, 5), Site(bortle=5))["margin"] for d in (100, 200, 400)]
    assert margins == sorted(margins)


def test_darker_sky_never_hurts_visibility():
    """Test that a darker sky never lowers the margin.
    """
    margins = [explain("M51", Telescope(200, 5), Site(bortle=b))["margin"] for b in range(9, 0, -1)]
    assert margins == sorted(margins)
