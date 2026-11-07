"""Offline lookup of deep-sky objects in the bundled OpenNGC catalogue.

The data in maglimit/data/openngc.csv comes from OpenNGC by Mattia Verga
(https://github.com/mattiaverga/OpenNGC), CC-BY-SA-4.0; see
maglimit/data/LICENSE-OpenNGC. It is rebuilt with scripts/build_catalogue.py.
"""
import csv
import difflib
import functools
import re
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class CatalogueObject:
    """A deep-sky object from the catalogue.

    Args:
        name: display name, such as "NGC 224"
        messier: Messier number, or None
        type: OpenNGC type code, such as "G" or "PN"
        magnitude: visual magnitude, or None if unknown
        major_axis: major axis in arcmin, or None if unknown
        minor_axis: minor axis in arcmin, or None if unknown
        ra: right ascension in degrees
        dec: declination in degrees
        common_names: common names, such as "Andromeda Galaxy"
        flags: notes on the data: "magnitude_estimated", "round_assumed", "no_size"
    """
    name: str
    messier: int | None
    type: str
    magnitude: float | None
    major_axis: float | None
    minor_axis: float | None
    ra: float
    dec: float
    common_names: tuple[str, ...]
    flags: tuple[str, ...]


def normalise(name):
    """Reduces a name to the form used for lookup

    Args:
        name: object name as typed, such as "NGC 0224" or "M031"

    Returns:
        Lowercase name with spaces and leading zeros removed, such as "ngc224"
    """
    name = re.sub(r"\s+", "", name.lower())
    return re.sub(r"(?<![\d.])0+(?=\d)", "", name)


def _number(text):
    """Returns a float, or None for an empty field
    """
    return float(text) if text else None


def _split(text):
    """Splits a |-separated field
    """
    return tuple(text.split("|")) if text else ()


@functools.cache
def _load():
    """Reads the bundled catalogue and builds the lookup index
    """
    objects, aliases = [], []
    with (files("maglimit")/"data/openngc.csv").open(encoding="utf-8") as data:
        for row in csv.DictReader(data):
            obj = CatalogueObject(
                name=row["name"],
                messier=int(row["messier"]) if row["messier"] else None,
                type=row["type"],
                magnitude=_number(row["magnitude"]),
                major_axis=_number(row["major"]),
                minor_axis=_number(row["minor"]),
                ra=_number(row["ra"]),
                dec=_number(row["dec"]),
                common_names=_split(row["common_names"]),
                flags=_split(row["flags"]),
            )
            objects.append(obj)
            aliases.append(_split(row["aliases"]))
    # An object's own name wins over another object's cross-reference
    index = {normalise(obj.name): obj for obj in objects}
    for obj, names in zip(objects, aliases):
        for alias in names:
            index.setdefault(alias, obj)
    return tuple(objects), index


def load_catalogue():
    """Returns every object in the bundled catalogue

    Returns:
        Tuple of CatalogueObject
    """
    return _load()[0]


def find_object(name):
    """Finds an object by Messier, NGC, IC or Caldwell number, or common name

    Args:
        name: object name, such as "M31", "NGC 224", "C 20" or "Andromeda Galaxy"

    Returns:
        CatalogueObject

    Raises:
        ValueError: if no object has that name, listing close matches
    """
    index = _load()[1]
    key = normalise(name)
    if key in index:
        return index[key]
    matches = difflib.get_close_matches(key, index, n=5)
    suggestions = list(dict.fromkeys(index[m].name if index[m].messier is None
                                     else f"M{index[m].messier}" for m in matches))
    hint = f"; did you mean {', '.join(suggestions)}?" if suggestions else ""
    raise ValueError(f"no object called {name!r} in the catalogue{hint}")
