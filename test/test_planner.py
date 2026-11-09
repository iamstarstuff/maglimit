import json
import re
import time
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from maglimit import planner
from maglimit.catalogue import find_object
from maglimit.planner import explain, tonight
from maglimit.site import Site
from maglimit.telescope import Telescope
from maglimit.visibility import extinction, moon_sky_brightness


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


PUNE = Site(lat=18.5, lon=73.9, bortle=5)
SCOPE = Telescope(200, 5, eyepieces=[32, 25, 10])
NIGHT = {"date": "2026-11-01", "tz": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def plan():
    """The default plan for a 200 mm f/5 at Pune on 2026-11-01.
    """
    return tonight(SCOPE, PUNE, **NIGHT)


def test_explain_unchanged_by_refactor():
    """Test that explain() still gives 0.3's answer for M33 under Bortle 7.
    """
    result = explain("M33", Telescope(200, 5), Site(bortle=7))
    assert (result["verdict"], result["margin"]) == ("challenging", 0.82)


def test_tonight_lists_believable_targets(plan):
    """Test that the Pune November list has well-known targets and only visible ones.
    """
    names = list(plan["name"])
    assert len(names) == 20
    assert {"M31", "M45"} & set(names)
    assert all(m >= 0 for m in plan["margin"])
    assert all(a >= 20 for a in plan["altitude"].to_value("deg"))


def test_easy_goal_ranks_by_band_then_messier_then_brightness():
    """Test that the easy list keeps verdict bands in order, Messier objects first.
    """
    full = tonight(SCOPE, PUNE, limit=200, **NIGHT)
    bands = [planner.BANDS.index(v) for v in full["verdict"]]
    assert bands == sorted(bands)
    easy = [re.fullmatch(r"M\d+", name) is not None
            for name, v in zip(full["name"], full["verdict"]) if v == "easy"]
    assert easy == sorted(easy, reverse=True)
    assert full["name"][0] == "M31"
    assert full.meta["goal"] == "easy"


def test_challenge_goal_puts_hardest_first():
    """Test that the challenge list starts with objects only just above threshold.
    """
    hard = tonight(SCOPE, PUNE, goal="challenge", **NIGHT)
    assert list(hard["margin"]) == sorted(hard["margin"])
    assert hard["margin"][0] < 0.5


def test_object_that_never_rises_is_left_out():
    """Test that NGC 2070, peaking near 2.5 degrees from Pune, isn't listed or counted.
    """
    full = tonight(SCOPE, PUNE, limit=100000, show_hidden=True, **NIGHT)
    assert "NGC 2070" not in set(full["catalogue_name"])


def test_hidden_objects_counted_and_shown(plan):
    """Test that objects up but below threshold are counted, and listed on request.
    """
    assert plan.meta["hidden"] > 0
    full = tonight(SCOPE, PUNE, limit=5, show_hidden=True, **NIGHT)
    assert full["verdict"][-1] == "not visible"


def test_types_filter():
    """Test that types= keeps only the chosen groups.
    """
    pns = tonight(SCOPE, PUNE, types=["pn"], **NIGHT)
    assert set(pns["type"]) == {"PN"}


def test_unknown_type_group_is_refused():
    """Test that an unknown type group names the valid ones.
    """
    with pytest.raises(ValueError, match="galaxy"):
        tonight(SCOPE, PUNE, types=["quasar"], **NIGHT)


def test_bad_goal_is_refused():
    """Test that a goal other than easy or challenge is refused.
    """
    with pytest.raises(ValueError, match="easy"):
        tonight(SCOPE, PUNE, goal="pretty", **NIGHT)


def test_meta_describes_the_night(plan):
    """Test that the table's meta has the darkness window, Moon and sky.
    """
    assert plan.meta["dark_start"] < plan.meta["dark_end"]
    assert plan.meta["moon_illumination"] == pytest.approx(0.5, abs=0.05)
    assert plan.meta["sky_sqm"] == 20.0


def test_higher_never_hurts():
    """Test that the same object at a higher altitude never gets a lower margin.
    """
    m13 = find_object("M13")
    margins = [planner._assess(m13, SCOPE, 20.0, 7.0, 2.0, extinction(a))[0]
               for a in range(20, 91, 10)]
    assert margins == sorted(margins)


def test_moon_lowers_margins():
    """Test that a full Moon near an object never raises its margin.
    """
    m33 = find_object("M33")
    dark = planner._assess(m33, SCOPE, 21.7, 7.0, 2.0)[0]
    moonlit = planner._assess(m33, SCOPE, moon_sky_brightness(21.7, 1.0, 20, 40), 7.0, 2.0)[0]
    assert moonlit < dark


def test_tonight_is_fast(plan):
    """Test that a full-catalogue night runs in under 2 seconds once the catalogue is loaded.
    """
    start = time.perf_counter()
    tonight(SCOPE, PUNE, **NIGHT)
    assert time.perf_counter() - start < 2.0


def test_running_night_drops_past_samples(monkeypatch):
    """Test that planning at 02:00 with no date only uses the rest of the night.
    """
    now = datetime(2026, 11, 2, 2, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    monkeypatch.setattr(planner, "_now", lambda zone: now)
    rest = tonight(SCOPE, PUNE, tz="Asia/Kolkata")
    assert rest.meta["date"] == "2026-11-01"
    assert rest.meta["dark_start"] >= now
    assert all(t.to_datetime(timezone=now.tzinfo) >= now for t in rest["best_time"])


def test_ended_night_is_a_clear_error(monkeypatch):
    """Test that planning after dawn but before noon says darkness has ended.
    """
    now = datetime(2026, 11, 2, 7, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    monkeypatch.setattr(planner, "_now", lambda zone: now)
    with pytest.raises(ValueError, match="darkness has ended"):
        tonight(SCOPE, PUNE, tz="Asia/Kolkata")


def test_system_zone_uses_tz_variable(monkeypatch):
    """Test that the system zone keeps its IANA name from TZ, so DST is followed.
    """
    monkeypatch.setenv("TZ", "Europe/London")
    assert planner._zone(None) == ZoneInfo("Europe/London")


def test_rounded_zero_margin_is_visible():
    """Test that hidden rows are all not visible and listed rows never are.
    """
    full = tonight(SCOPE, PUNE, limit=20, show_hidden=True, **NIGHT)
    listed, hidden = full[:20], full[20:]
    assert all(v != "not visible" for v in listed["verdict"])
    assert all(v == "not visible" for v in hidden["verdict"])
