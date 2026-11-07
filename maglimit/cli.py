import argparse
import json

from .planner import explain
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

    args = parser.parse_args(argv)
    try:
        args.run(args)
    except ValueError as error:
        args.parser.error(str(error))
    return 0
