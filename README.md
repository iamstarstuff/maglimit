<p align="center">
   <img src="https://raw.githubusercontent.com/iamstarstuff/maglimit/main/maglimit_logo.png" width=50% height=50%/>
</p>

# maglimit

[![codeastro](https://img.shields.io/badge/Made%20at-Code/Astro-blueviolet.svg)](https://semaphorep.github.io/codeastro/)
![](https://img.shields.io/github/license/iamstarstuff/maglimit)
[![pypi](https://img.shields.io/pypi/v/maglimit)](https://pypi.org/project/maglimit/)
[![DOI](https://zenodo.org/badge/506751105.svg)](https://zenodo.org/badge/latestdoi/506751105)
[![CI](https://github.com/iamstarstuff/maglimit/actions/workflows/ci.yml/badge.svg)](https://github.com/iamstarstuff/maglimit/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/maglimit/badge/?version=latest)](https://maglimit.readthedocs.io/en/latest/?badge=latest)

A package to determine observability of an astronomical object using its magnitude and telescope's limiting magnitude.
As a rule of thumb, the limiting magnitude of a telescope depends on the aperture of mirror / lens:


$$L_{mag} = 2 + 5\log{D_0}$$
Where $D_0$ is the aperture in mm. `lim_mag()` uses this formula and ignores the sky.

Since 0.3, maglimit can also tell you how well a deep-sky object will show, offline, with a graded verdict (easy, moderate, challenging, very hard or not visible), the best eyepiece and the numbers behind it. It uses the contrast-threshold model of [Crumey (2014), MNRAS 442, 2600](https://arxiv.org/abs/1405.4209), a fit to Blackwell's (1946) measurements of the dark-adapted eye, tested against historical telescope observations. `sky_lim_mag()`, the star limit under a given sky, uses the same model, so its numbers differ from 0.2.

Treat the answers as a guide: eyes vary by half a magnitude or more. The model's limits:
- it treats objects as evenly bright. Galaxies, globular clusters and M42 are also tested as a bright core holding half the light in a quarter of the diameter, a calibrated rule rather than physics from the paper;
- filters aren't modelled, and catalogue magnitudes for nebulae are unreliable, so nebulae get a low-confidence answer;
- objects are assumed to be at the zenith, with no Moon, until 0.4.

## Installation

Requires Python 3.10+.

```bash
pip install maglimit
```

or, in a uv project:

```bash
uv add maglimit
```

## Quick start

```python
import maglimit as ml

scope = ml.Telescope(aperture=100, fstop=4.5)   # 100 mm f/4.5
scope.lim_mag()                                  # 12.0
scope.magnification(f_eyepiece=25)               # 18.0
ml.is_object_observable("M31", scope.lim_mag())  # True (queries NED)
ml.smallest_scope("NGC 244", fs=4.5)             # (13.83, <Quantity 232.27 mm>, <Quantity 1045.22 mm>)

site = ml.Site(bortle=5)                         # or sqm=20.1
scope.sky_lim_mag(site)                          # 10.73, at low power
scope.sky_lim_mag(site, eyepiece=10)             # 11.72
scope.exit_pupil(25)                             # 5.56 (mm)
scope.dawes_limit()                              # 1.16 (arcseconds)

ml.find_object("andromeda galaxy")               # CatalogueObject(name='NGC 224', messier=31, ...)
result = ml.explain("M33", ml.Telescope(200, 5), ml.Site(bortle=7))
result["verdict"], result["margin"]              # ('challenging', 0.82)
```

From the command line, for a summary of a telescope and its eyepieces:

```bash
maglimit scope --aperture 200 --fstop 5 --eyepieces 32,25,10 --bortle 5
```

To check one object, with no network needed:

```bash
maglimit check M33 --aperture 200 --fstop 5 --bortle 7
```

Add `--json` to either command to get the same numbers as JSON.

## Development

```bash
git clone https://github.com/iamstarstuff/maglimit
cd maglimit
uv sync --all-groups
uv run pytest                     # add -m "not network" to skip the live NED test
uv run sphinx-build -b html docs docs/_build/html
```

Releases are published to PyPI from GitHub releases via trusted publishing (see `.github/workflows/publish.yml`).

 ## Tutorials
 You can find the tutorial here: [docs/Tutorial/limiting_magnitude.ipynb](https://github.com/iamstarstuff/maglimit/blob/main/docs/Tutorial/limiting_magnitude.ipynb)


## Data and license

maglimit is MIT licensed. The bundled catalogue, `maglimit/data/openngc.csv`, is derived from [OpenNGC](https://github.com/mattiaverga/OpenNGC) by Mattia Verga and is shared under CC-BY-SA-4.0; see `maglimit/data/LICENSE-OpenNGC`. Seven Messier magnitudes missing from OpenNGC are filled from Wikipedia's *List of Messier objects* (`maglimit/data/corrections.csv`). Rebuild it with `uv run python scripts/build_catalogue.py`.

 ## Future Goals:
 - We use [astroquery.ipac.ned](https://astroquery.readthedocs.io/en/latest/ipac/ned/ned.html) catalogue to query the object by Messier and NGC name. 
    Further we plan to add cross-catalogue query feature.