"""Builds maglimit/data/openngc.csv from the OpenNGC catalogue.

OpenNGC by Mattia Verga, https://github.com/mattiaverga/OpenNGC, CC-BY-SA-4.0.

Usage:
    uv run python scripts/build_catalogue.py            # download the pinned version
    uv run python scripts/build_catalogue.py --source DIR   # use NGC.csv and addendum.csv in DIR

The output keeps the fields maglimit needs, picks one visual magnitude per object,
applies maglimit/data/corrections.csv, and folds duplicate entries into the
aliases of the objects they point to.
"""
import argparse
import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from maglimit.catalogue import normalise

COMMIT = "be3cd6c5498806a2fbb2f7e0452ef802dbb02be0"
BASE_URL = f"https://raw.githubusercontent.com/mattiaverga/OpenNGC/{COMMIT}/"
DATA = Path(__file__).resolve().parents[1]/"maglimit"/"data"

DROPPED_TYPES = {"Dup", "NonEx", "*", "**", "Other", "Nova"}
GALAXY_TYPES = {"G", "GPair", "GTrpl", "GGroup"}
# Median B-V of OpenNGC galaxies with both magnitudes
B_MINUS_V = 0.76
FIELDS = ["name", "messier", "type", "ra", "dec", "major", "minor", "magnitude", "flags",
          "aliases", "common_names"]


def fetch(path, source):
    """Returns the text of an OpenNGC file, from a local folder or the pinned commit
    """
    if source:
        return (Path(source)/Path(path).name).read_text(encoding="utf-8")
    with urllib.request.urlopen(BASE_URL + path) as response:
        return response.read().decode("utf-8")


def display_name(name):
    """Turns an OpenNGC name such as NGC0224 into NGC 224, or M040 into M40
    """
    match = re.match(r"([A-Za-z]+)(\d+)(.*)", name)
    if not match:
        return name
    prefix, number, rest = match.groups()
    separator = "" if prefix == "M" else " "
    return f"{prefix}{separator}{int(number)}{rest}"


def degrees(text, hours):
    """Converts sexagesimal RA (hours) or Dec (degrees) to decimal degrees
    """
    if not text:
        return ""
    sign = -1 if text.startswith("-") else 1
    a, b, c = (float(part) for part in text.lstrip("+-").split(":"))
    value = sign*(a + b/60 + c/3600)*(15 if hours else 1)
    return f"{value:.5f}"


def number(text):
    """Returns a float, or None for an empty field
    """
    return float(text) if text.strip() else None


def magnitude(row):
    """Picks a visual magnitude and says whether it was estimated from B
    """
    b, v = number(row["B-Mag"]), number(row["V-Mag"])
    if row["Type"] in GALAXY_TYPES and b is not None and (v is None or not -0.2 <= b - v <= 2):
        return b - B_MINUS_V, True
    if v is None and b is not None:
        return b - B_MINUS_V, True
    return v, False


def catalogue_aliases(row):
    """Returns the lookup names given in a row's own columns
    """
    names = [row["Name"]]
    if row["M"]:
        names.append(f"M{int(row['M'])}")
    names += [f"NGC{n.strip()}" for n in row["NGC"].split(",") if n.strip()]
    names += [f"IC{n.strip()}" for n in row["IC"].split(",") if n.strip()]
    names += [i for i in row["Identifiers"].split(",") if re.match(r"C \d+$", i.strip())]
    return names


def build(source=None):
    """Builds the catalogue rows

    Returns:
        List of dictionaries with the FIELDS columns
    """
    rows = []
    for path in ("database_files/NGC.csv", "database_files/addendum.csv"):
        rows += csv.DictReader(io.StringIO(fetch(path, source)), delimiter=";")
    corrections = list(csv.DictReader((DATA/"corrections.csv").open(encoding="utf-8")))

    kept, duplicates = {}, []
    for row in rows:
        if row["Type"] == "Dup":
            duplicates.append(row)
        elif row["Type"] not in DROPPED_TYPES or row["M"]:
            kept[row["Name"]] = row

    objects = {}
    for name, row in kept.items():
        flags = []
        mag, estimated = magnitude(row)
        if estimated:
            flags.append("magnitude_estimated")
        major, minor = number(row["MajAx"]), number(row["MinAx"])
        if major is None:
            flags.append("no_size")
            minor = None
        elif minor is None:
            minor = major
            flags.append("round_assumed")
        common = [c.strip() for c in row["Common names"].split(",") if c.strip()]
        objects[name] = {
            "name": display_name(name),
            "messier": int(row["M"]) if row["M"] else "",
            "type": row["Type"],
            "ra": degrees(row["RA"], hours=True),
            "dec": degrees(row["Dec"], hours=False),
            "major": "" if major is None else major,
            "minor": "" if minor is None else minor,
            "magnitude": "" if mag is None else round(mag, 2),
            "flags": flags,
            "aliases": [normalise(a) for a in catalogue_aliases(row)] + [normalise(c) for c in common],
            "common_names": common,
        }

    index = {normalise(name): name for name in objects}
    for name, obj in objects.items():
        for alias in obj["aliases"]:
            index.setdefault(alias, name)

    for row in duplicates:
        targets = [normalise(a) for a in catalogue_aliases(row)[1:]]
        target = next((index[t] for t in targets if t in index), None)
        if target:
            objects[target]["aliases"].append(normalise(row["Name"]))

    for correction in corrections:
        obj = objects[correction["name"]]
        obj[correction["field"]] = float(correction["value"])
        if correction["field"] == "magnitude" and "magnitude_estimated" in obj["flags"]:
            obj["flags"].remove("magnitude_estimated")

    for obj in objects.values():
        obj["aliases"] = "|".join(dict.fromkeys(obj["aliases"]))
        obj["flags"] = "|".join(obj["flags"])
        obj["common_names"] = "|".join(obj["common_names"])
    return list(objects.values())


def main():
    """Writes the catalogue and OpenNGC's license into maglimit/data
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", help="folder with NGC.csv, addendum.csv and CC-BY-SA-4.0.txt")
    args = parser.parse_args()
    rows = build(args.source)
    with (DATA/"openngc.csv").open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    license_text = fetch("LICENSES/CC-BY-SA-4.0.txt", args.source)
    (DATA/"LICENSE-OpenNGC").write_text(
        "maglimit/data/openngc.csv is derived from OpenNGC by Mattia Verga,\n"
        f"https://github.com/mattiaverga/OpenNGC (commit {COMMIT}),\n"
        "and is shared under the same license, reproduced below. The rest of\n"
        "maglimit is MIT licensed.\n\n" + license_text, encoding="utf-8")
    print(f"wrote {len(rows)} objects")


if __name__ == "__main__":
    main()
