import pytest

from maglimit.catalogue import find_object, load_catalogue, normalise


@pytest.mark.parametrize("text", ["M31", "m31", "M 31", "M031", "NGC 224", "ngc224", "NGC0224",
                                  "Andromeda Galaxy", "andromeda galaxy"])
def test_ways_of_naming_m31(text):
    """Test that the usual ways of writing M31's names all find it.
    """
    assert find_object(text).messier == 31


def test_normalise():
    """Test that names are reduced to one lookup form.
    """
    assert normalise("NGC 0224") == "ngc224"
    assert normalise("M031") == "m31"


def test_caldwell_alias():
    """Test lookup by Caldwell number.
    """
    assert find_object("C 20").name == "NGC 7000"


def test_duplicate_follows_to_main_object():
    """Test that M102, listed as a duplicate of M101, finds M101.
    """
    assert find_object("M102") == find_object("M101")


def test_all_messier_objects_are_found():
    """Test that every Messier number resolves.
    """
    for number in range(1, 111):
        assert find_object(f"M{number}")


def test_unknown_name_suggests_matches():
    """Test that an unknown name gives an error naming close matches.
    """
    with pytest.raises(ValueError, match="M31"):
        find_object("M311")
    with pytest.raises(ValueError):
        find_object("not an object")


def test_bad_v_magnitude_uses_b():
    """Test that NGC 253's implausible V magnitude is replaced from B.
    """
    assert find_object("NGC 253").magnitude == pytest.approx(7.18)
    assert "magnitude_estimated" in find_object("NGC 253").flags


def test_correction_fills_missing_magnitude():
    """Test that corrections.csv fills Messier objects with no magnitude.
    """
    assert find_object("M22").magnitude == pytest.approx(5.1)
    assert find_object("M35").magnitude == pytest.approx(5.3)


def test_missing_minor_axis_assumes_round():
    """Test that an object with only a major axis is treated as round.
    """
    obj = find_object("M13")
    assert obj.minor_axis == obj.major_axis
    assert "round_assumed" in obj.flags


def test_object_with_no_size_is_flagged():
    """Test that an object with no size is flagged.
    """
    assert "no_size" in find_object("M40").flags


def test_stars_are_left_out_unless_messier():
    """Test that duplicates and non-existent objects are not in the catalogue.
    """
    types = {obj.type for obj in load_catalogue()}
    assert not types & {"Dup", "NonEx"}


def test_catalogue_is_bundled_and_substantial():
    """Test that the bundled catalogue holds the NGC and IC objects.
    """
    assert len(load_catalogue()) > 12000
