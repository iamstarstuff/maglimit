import argparse
import json
import math
from datetime import datetime
from zoneinfo import ZoneInfoNotFoundError

from .planner import GOALS, explain, tonight
from .site import Site, bortle_to_sqm
from .telescope import Eyepiece, Telescope


def _focal_lengths(text):
    """Parses a comma-separated list of eyepiece focal lengths, eg: 32,25,10
    """
    try:
        return [float(value) for value in text.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected focal lengths in mm like 32,25,10, got {text!r}"
        ) from None


# Words for OpenNGC type codes in the tonight table
TYPE_LABELS = {
    "G": "Galaxy", "GPair": "Galaxy pair", "GTrpl": "Galaxy trio", "GGroup": "Galaxy group",
    "GCl": "Globular", "OCl": "Open cluster", "*Ass": "Asterism", "PN": "Planetary",
    "HII": "HII region", "Neb": "Nebula", "EmN": "Emission nebula",
    "RfN": "Reflection nebula", "SNR": "Supernova remnant", "Cl+N": "Cluster+nebula",
    "**": "Double star", "Other": "Other",
}


def _types(text):
    """Parses a comma-separated list of type groups, eg: galaxy,pn
    """
    return [value.strip() for value in text.split(",") if value.strip()]


def _sky_label(site):
    """Describes the sky the way the user gave it
    """
    if site.bortle is not None and site.sqm == bortle_to_sqm(site.bortle):
        return f"Bortle {site.bortle} (SQM ~{site.sqm:.1f})"
    return f"SQM {site.sqm:.1f}"


def _eyepiece_table(eyepieces, with_sky):
    """Formats the per-eyepiece rows of a scope summary
    """
    header = ["Eyepiece", "Mag", "Exit pupil", "True field"]
    if with_sky:
        header.append("Star limit")
    rows = [header]
    for eyepiece in eyepieces:
        row = [
            f"{eyepiece['focal_length_mm']:g} mm",
            f"{eyepiece['magnification']:g}x",
            f"{eyepiece['exit_pupil_mm']:g} mm",
            f"{eyepiece['true_field_deg']:g} deg",
        ]
        if with_sky:
            row.append(f"{eyepiece['sky_star_limit']:.2f}")
        rows.append(row)
    widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    lines = []
    for row, notes in zip(rows, [[]] + [e["notes"] for e in eyepieces]):
        line = "  ".join(cell.ljust(width) for cell, width in zip(row, widths))
        lines.append(f"{line}  {'; '.join(notes)}".rstrip())
    return lines


def _format_summary(summary, site):
    """Formats a scope summary as text for the terminal
    """
    lines = [
        f"{summary['aperture_mm']:g} mm f/{summary['fstop']:g}, focal length "
        + f"{summary['focal_length_mm']:g} mm",
        f"Rule-of-thumb star limit: {summary['star_limit']:.2f}",
    ]
    if site is not None:
        lines.append(f"Sky: {_sky_label(site)}")
        lines.append(f"Star limit under this sky, low power: {summary['sky_star_limit']:.2f}")
    lines.append(f"Dawes limit: {summary['dawes_limit_arcsec']:g} arcsec")
    lines.append(
        f"Useful magnification: {summary['min_magnification']:g}x "
        f"to {summary['max_magnification']:g}x"
    )
    if summary["eyepieces"]:
        lines.append("")
        lines.extend(_eyepiece_table(summary["eyepieces"], site is not None))
    return "\n".join(lines)


def _scope(args):
    """Runs the scope command
    """
    site = None
    if args.bortle is not None or args.sqm is not None:
        site = Site(bortle=args.bortle, sqm=args.sqm)
    eyepieces = [Eyepiece(focal_length, args.afov) for focal_length in args.eyepieces]
    scope = Telescope(args.aperture, args.fstop, eyepieces, args.obstruction)
    summary = scope.summary(site, args.eye_pupil)
    print(json.dumps(summary, indent=2) if args.json else _format_summary(summary, site))


def _format_check(result, site):
    """Formats an explain() result as text for the terminal
    """
    obj = result["object"]
    name = obj["name"]
    if obj["messier"] is not None and name != f"M{obj['messier']}":
        name = f"M{obj['messier']} ({name})"
    common = f", {obj['common_names'][0]}" if obj["common_names"] else ""
    lines = [f"{name}{common}, type {obj['type']}, magnitude {obj['magnitude']:g}"]
    lines.append(f"Verdict: {result['verdict']} (seen as {result['seen_as']})")
    if result["surface_brightness"] is None:
        lines.append("Surface brightness: unknown, no size in the catalogue")
    else:
        lines.append(f"Surface brightness: {result['surface_brightness']:.2f} mag/arcsec^2")
    sky = f"Sky: {result['sky_sqm']:.1f} mag/arcsec^2"
    if site.bortle is not None and site.sqm == bortle_to_sqm(site.bortle):
        sky += f", typical for Bortle {site.bortle}"
    lines.append(sky)
    lines.append(f"Margin above threshold: {result['margin']:+.2f} mag")
    power = f"{result['best_magnification']:g}x, exit pupil {result['best_exit_pupil']:g} mm"
    if result["best_eyepiece"] is not None:
        power = f"{result['best_eyepiece']:g} mm eyepiece, {power}"
    lines.append(f"Best view: {power}")
    if result["confidence"] == "low":
        lines.append("Low confidence: " + "; ".join(result["reasons"]))
    lines.append("Assumes: " + "; ".join(result["assumes"]))
    return "\n".join(lines)


def _check(args):
    """Runs the check command
    """
    site = Site(bortle=args.bortle, sqm=args.sqm)
    eyepieces = [Eyepiece(focal_length, args.afov) for focal_length in args.eyepieces]
    scope = Telescope(args.aperture, args.fstop, eyepieces, args.obstruction)
    result = explain(args.object, scope, site, args.eye_pupil)
    print(json.dumps(result, indent=2) if args.json else _format_check(result, site))


def _size(row):
    """Formats an object's size in arcmin, or - when unknown
    """
    if math.isnan(row["major_axis"]):
        return "-"
    if row["major_axis"] == row["minor_axis"]:
        return f"{row['major_axis']:.3g}'"
    return f"{row['major_axis']:.3g}'x{row['minor_axis']:.3g}'"


def _local(time, zone):
    """Converts an astropy Time to a local datetime
    """
    return time.to_datetime(timezone=zone)


def _format_tonight(plan, scope, site):
    """Formats a tonight() table as text for the terminal
    """
    meta = plan.meta
    zone = meta["dark_start"].tzinfo
    lines = [
        (f"Tonight ({meta['date']}), {_sky_label(site)}, dark from "
         f"{meta['dark_start']:%H:%M} to {meta['dark_end']:%H:%M}"),
        f"{scope._aperture_mm():g} mm f/{scope.fstop:g}, star limit ~{meta['star_limit']:.2f}",
        f"Moon: {meta['moon_illumination']:.0%} lit",
        "",
    ]
    rows = [["#", "Object", "Type", "Mag", "Size", "Best", "Alt", "Eyepiece", "Verdict"]]
    low = False
    for number, row in enumerate(plan, start=1):
        power = f"{row['magnification']:.0f}x"
        if not math.isnan(row["eyepiece"]):
            power = f"{row['eyepiece']:g} mm {power}"
        judged = row["verdict"]
        if row["seen_as"] == "bright core":
            judged += " (core only)"
        if row["confidence"] == "low":
            judged += " *"
            low = True
        rows.append([
            str(number), row["name"], TYPE_LABELS.get(row["type"], row["type"]),
            f"{row['magnitude']:.1f}", _size(row), f"{_local(row['best_time'], zone):%H:%M}",
            f"{row['altitude'].to_value('deg'):.0f}°", power, judged,
        ])
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for row in rows:
        cells = [row[0].rjust(widths[0])] + [c.ljust(w) for c, w in zip(row[1:], widths[1:])]
        lines.append(" " + "  ".join(cells).rstrip())
    if len(plan) == 0:
        lines.append("Nothing above threshold tonight.")
    if low:
        lines.append("* low confidence; use maglimit check NAME for reasons")
    if meta["hidden"]:
        lines.append(f"Not shown: {meta['hidden']} objects up but below threshold "
                     "(use --show-hidden)")
    return "\n".join(lines)


def _plain(value, zone):
    """Turns a table value into something JSON can hold
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "to_datetime"):
        return _local(value, zone).isoformat()
    if hasattr(value, "unit"):
        value = value.value
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _tonight_json(plan):
    """Returns a tonight() table as plain data for --json
    """
    zone = plan.meta["dark_start"].tzinfo
    return {
        "meta": {key: _plain(value, zone) for key, value in plan.meta.items()},
        "objects": [{name: _plain(row[name], zone) for name in plan.colnames} for row in plan],
    }


def _tonight(args):
    """Runs the tonight command
    """
    site = Site(lat=args.lat, lon=args.lon, bortle=args.bortle, sqm=args.sqm)
    eyepieces = [Eyepiece(focal_length, args.afov) for focal_length in args.eyepieces]
    scope = Telescope(args.aperture, args.fstop, eyepieces, args.obstruction)
    try:
        plan = tonight(scope, site, date=args.date, tz=args.tz, types=args.types,
                       goal=args.goal, limit=args.limit, min_altitude=args.min_altitude,
                       sun_altitude=args.sun_altitude, show_hidden=args.show_hidden,
                       eye_pupil=args.eye_pupil)
    except ZoneInfoNotFoundError:
        raise ValueError(f"unknown time zone {args.tz!r}; use a name like Asia/Kolkata") from None
    except ValueError as error:
        raise ValueError(str(error).replace("sun_altitude=-12", "--sun-altitude -12")) from None
    if args.json:
        print(json.dumps(_tonight_json(plan), indent=2))
    else:
        print(_format_tonight(plan, scope, site))


def _add_scope_arguments(parser, sky_required):
    """Adds the telescope, sky and output arguments shared by the commands
    """
    parser.add_argument("--aperture", type=float, required=True, help="aperture in mm")
    parser.add_argument("--fstop", type=float, required=True, help="focal ratio")
    parser.add_argument("--eyepieces", type=_focal_lengths, default=[],
                        help="eyepiece focal lengths in mm, eg: 32,25,10")
    parser.add_argument("--afov", type=float, default=52.0,
                        help="apparent field of the eyepieces in degrees (default: 52)")
    parser.add_argument("--obstruction", type=float, default=0.0,
                        help="central obstruction as a fraction of the aperture (default: 0)")
    sky = parser.add_mutually_exclusive_group(required=True) if sky_required else parser
    sky.add_argument("--bortle", type=int, help="sky darkness, Bortle class from 1 to 9")
    sky.add_argument("--sqm", type=float, help="sky darkness, measured in mag/arcsec^2")
    parser.add_argument("--eye-pupil", type=float, default=7.0,
                        help="dark-adapted eye pupil in mm (default: 7)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def main(argv=None):
    """Runs the maglimit command line tool

    Args:
        argv: command line arguments, defaults to the ones the program was started with

    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(prog="maglimit", description="Plan what your telescope can show you.")
    commands = parser.add_subparsers(dest="command", required=True)

    scope = commands.add_parser("scope", help="summarise a telescope and its eyepieces")
    _add_scope_arguments(scope, sky_required=False)
    scope.set_defaults(run=_scope, parser=scope)

    check = commands.add_parser("check", help="say how well an object can be seen")
    check.add_argument("object", help="object name, eg: M33, 'NGC 7000' or 'Ring Nebula'")
    _add_scope_arguments(check, sky_required=True)
    check.set_defaults(run=_check, parser=check)

    plan = commands.add_parser("tonight", help="rank what's worth looking at tonight")
    _add_scope_arguments(plan, sky_required=True)
    plan.add_argument("--lat", type=float, required=True, help="latitude in degrees, north positive")
    plan.add_argument("--lon", type=float, required=True, help="longitude in degrees, east positive")
    plan.add_argument("--date", help="date the night starts, YYYY-MM-DD (default: tonight)")
    plan.add_argument("--tz", help="time zone, eg: Asia/Kolkata (default: the system's)")
    plan.add_argument("--limit", type=int, default=20, help="objects to list (default: 20)")
    plan.add_argument("--types", type=_types,
                      help="type groups to keep: galaxy, globular, open, nebula, pn")
    plan.add_argument("--goal", choices=GOALS, default="easy",
                      help="easy: easiest first (default); challenge: hardest still visible first")
    plan.add_argument("--min-altitude", type=float, default=20.0,
                      help="lowest useful altitude in degrees (default: 20)")
    plan.add_argument("--sun-altitude", type=float, default=-18.0,
                      help="the Sun must be below this altitude for darkness (default: -18)")
    plan.add_argument("--show-hidden", action="store_true",
                      help="also list objects that are up but below threshold")
    plan.set_defaults(run=_tonight, parser=plan)

    args = parser.parse_args(argv)
    try:
        args.run(args)
    except ValueError as error:
        args.parser.error(str(error))
    return 0
