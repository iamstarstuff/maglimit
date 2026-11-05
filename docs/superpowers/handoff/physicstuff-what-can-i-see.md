# Handoff to physicstuff.com: "What can I see tonight?" tool and post series

**For:** the Claude session working in the physicstuff.com repo.
**From:** the maglimit project (https://github.com/iamstarstuff/maglimit), 2026-11-05.
**Copy this file into the physicstuff repo** (for example under `docs/`) and work from there.
Check the repo's own `CLAUDE.md`, `PRODUCT.md` and `DESIGN.md` first: their rules on posts,
simulations and style take priority over anything here.

## 1. What this is

maglimit is Pratik's open-source Python package. It is growing from "is this object brighter
than my telescope's limit?" into a planner: given a telescope, eyepieces, sky darkness,
location and date, it ranks the deep-sky objects worth looking at tonight, with the best time,
a recommended eyepiece and a graded verdict (easy / moderate / challenging / very hard / not
visible).

physicstuff.com gets two things from this:

1. **A series of concept posts** explaining every term the tool uses.
2. **The tool itself**, as an interactive page where anyone can find out what to look at.

Audience: experienced observers, beginners at outreach events, and students/educators. That
overlaps with the audience in `PRODUCT.md`.

## 2. Decisions already made (don't reopen without Pratik)

- The site tool is a **TypeScript port running in the browser**. No Python on the site, no
  API, no Pyodide. It follows the usual three-file pattern: engine in `src/lib/simulations/`,
  component in `src/components/simulations/`, MDX article in `src/content/`.
- The **Python package is the source of truth** for the maths. If the two disagree, the
  Python is right unless Pratik decides the model itself should change, and that change is
  made in maglimit first.
- Catalogue: **OpenNGC**, license CC-BY-SA-4.0. Attribution must appear on the tool page, and
  the catalogue file stays under that license.
- Ranking: easiest first by default, with a "challenge" option for the best target you can
  still just see.
- Moon, first version: show phase and distance from the object, and apply a simple penalty.
- Verdicts are always graded, never a bare yes/no. A confident wrong answer is the worst
  failure this tool can have, particularly for a beginner.
- Astrophotography is out of scope for now.

**Still open, for Pratik to decide:** where the tool lives on the site (for example
`/lab/what-can-i-see` or `/astrophysics/what-can-i-see-tonight`), and whether the post list
below is complete.

## 3. What exists today, and what doesn't

maglimit release plan:

| Release | Adds | Status on 2026-11-05 |
|---|---|---|
| 0.1 | Packaging, basic `Telescope`, simple limiting magnitude | In review (PR #6), not on PyPI yet |
| 0.2 | Eyepieces, exit pupil, field of view, Dawes limit, Bortle/SQM, sky-aware star limit | Being planned |
| 0.3 | Bundled catalogue, surface brightness, contrast-threshold visibility model | Not started |
| 0.4 | `maglimit tonight`: altitude, darkness, Moon, ranking | Not started |
| 0.5 | Notebook support, JSON output | Not started |
| 0.6 | **Web export: the data files the site needs (section 5)** | Not started |

So:

- **Start now:** posts 1–6 below. They need no tool, only the physics.
- **Wait for 0.3:** posts 7–8, so their numbers match the model that ships. Drafting the
  explanation earlier is fine.
- **Wait for 0.6:** the TypeScript engine and tool page. Don't invent the model or the data
  format ahead of it. Everything in section 5 is the planned shape and may still change.

Check the maglimit repo for current status before relying on this table.

## 4. Post series

Each post stands alone and has its own small interactive. The series builds toward post 11.
Check `src/config/posts.ts` for overlap first; link to or extend an existing post rather than
repeating it.

| # | Post | Subject | Small interactive | Role in the tool |
|---|---|---|---|---|
| 1 | What is magnitude? The backwards, logarithmic scale of star brightness | astrophysics | Compare brightness ratios | Every number shown |
| 2 | Why a bigger telescope sees fainter: aperture and limiting magnitude | optics | Aperture slider vs faintest star | Star limit |
| 3 | Focal ratio, magnification and what eyepieces really do | optics | Scope + eyepiece calculator | Scope summary |
| 4 | Exit pupil: why more magnification isn't always better | optics | Exit pupil vs your eye | Eyepiece choice |
| 5 | Resolving power: the Dawes limit and double stars | optics | Two stars merging | Scope summary |
| 6 | Bortle scale and SQM: measuring how dark your sky is | astrophysics | Bortle slider | Sky input |
| 7 | Surface brightness: why M31 is "bright" yet hard to see | astrophysics | Same light spread over bigger areas | Core of the model |
| 8 | How the eye detects faint things: contrast thresholds | optics | Interactive detection test | Core of the model |
| 9 | Airmass and extinction: why objects fade near the horizon | astrophysics | Altitude slider | Altitude penalty |
| 10 | Twilight, moonlight and when the sky is actually dark | astrophysics | Night timeline | Darkness window |
| 11 | What can I see tonight? (the tool) | astrophysics | The full planner | Launch post |

Posts 7 and 8 are the most distinctive and the likeliest to do well in search.

### Physics reference for the posts

These are the relations maglimit uses or plans to use. Verify them against primary sources
while writing; they are a starting point, not a citation.

- **Magnitude:** 5 magnitudes = a factor of 100 in brightness, so 1 magnitude ≈ 2.512×.
- **Simple limiting magnitude:** `L = 2 + 5·log10(D)`, D in mm. A rule of thumb: 100 mm gives
  12.0, 200 mm gives 13.51. It ignores sky brightness completely, which is the point of the
  later posts.
- **Focal length** = aperture × f-ratio. **Magnification** = telescope focal length ÷ eyepiece
  focal length.
- **Exit pupil** (mm) = aperture ÷ magnification = eyepiece focal length ÷ f-ratio. A 200 mm
  f/5 scope with a 32 mm eyepiece gives 31× and a 6.4 mm exit pupil.
- **True field** ≈ eyepiece apparent field ÷ magnification.
- **Useful magnification:** about D/7 at the low end (exit pupil matches a 7 mm eye), and
  about 2×D at the high end, with D in mm.
- **Dawes limit:** about 116 ÷ D arcseconds, D in mm.
- **Naked-eye limit from sky brightness:** `NELM ≈ 7.93 − 5·log10(10^(4.316 − SQM/5) + 1)`,
  giving about 6.6 at SQM 22 and about 4.0 at SQM 18.
- **Surface brightness:** `SB = m + 2.5·log10(area in arcsec²)`, with area = π/4 · a · b for an
  ellipse. M31 (B ≈ 4.29, 178′ × 70′) averages about 23.1 mag/arcsec², which is fainter per
  unit area than a dark sky at about 22. That's why you see the core and not the whole
  galaxy.
- **Key idea for post 8:** a telescope can't increase an extended object's contrast against
  the sky. Object and sky dim together as magnification goes up, while the object's apparent
  size grows. The eye's detection threshold depends on both brightness and size, so there's
  a best magnification for each object. Sources: Blackwell (1946), and Roger Clark, *Visual
  Astronomy of the Deep Sky* (1990).
- **Telescopic limit with sky brightness:** Schaefer (1990).
- **Extinction:** dimming ≈ k × airmass, with k ≈ 0.25 mag per airmass in V as a typical
  value.
- **Twilight:** astronomical darkness starts when the Sun is 18° below the horizon.
- **Moonlit sky** (later): Krisciunas & Schaefer (1991).

Catalogue magnitudes vary by source (M31: V 3.44 in OpenNGC, 4.36 from NED). If a post quotes
one, say which, or give a rounded value.

## 5. Using maglimit for the tool

### Planned data files (from 0.6)

maglimit will produce these with a script. Copy or sync them into this repo (`data/` or
`public/`) rather than editing them by hand:

| File | Contents |
|---|---|
| Catalogue JSON | Trimmed OpenNGC: name, type, RA/Dec, axes, magnitudes, common names, flags for filled-in values |
| Threshold table | The contrast-threshold data the visibility model looks up |
| Conformance file | Inputs and expected outputs generated by the Python code |

**The conformance file is the safety net.** Run every case through the TypeScript engine in a
vitest test. A failing case means the port is wrong (or out of date), not that the test needs
adjusting. Don't launch the tool until it all passes, including the "golden" cases of known
objects from city and dark sites.

The catalogue is about 1 MB before compression. Consider loading a smaller set first
(Messier, Caldwell, brightest NGC/IC) and fetching the rest on demand.

### What the TypeScript engine needs

- Optics formulas (section 4).
- Surface brightness and the threshold lookup, exactly as in maglimit's visibility code.
- Sun/Moon positions: use a library such as `astronomy-engine` rather than hand-written
  formulas. Check its license and size first. Minute-level accuracy is plenty.
- Altitude and airmass per object, sampled across the dark window.

### Using the Python package while developing

Handy for checking values by hand. The first block works with the code in PR #6 (run
`uv sync` in the maglimit repo; PyPI still has the old 0.0.2):

```python
import maglimit as ml

scope = ml.Telescope(aperture=200, fstop=5)
scope.focal_length()      # <Quantity 1000. mm>
scope.lim_mag()           # 13.51
scope.magnification(32)   # 31.25
```

The planned interface, which **doesn't exist yet and may change**:

```bash
maglimit scope --aperture 200 --fstop 5 --eyepieces 32,25,10
maglimit check M33 --aperture 200 --fstop 5 --bortle 7
maglimit tonight --aperture 200 --fstop 5 --eyepieces 32,25,10 --lat 18.5 --lon 73.9 --bortle 5
```

```python
scope = ml.Telescope(aperture=200, fstop=5, eyepieces=[32, 25, 10])
site = ml.Site(lat=18.5, lon=73.9, bortle=5)      # or sqm=20.1
plan = ml.tonight(scope, site, date="2026-11-01")
ml.explain("NGC 891", scope, site)                # the numbers behind one verdict
```

## 6. The tool page

Follow the site's layered contract (layman → simulation → derivation), its existing components
(`SimulationLayout`, `ParamSlider`) and the four-ink palette.

- **Inputs:** aperture, f-ratio, eyepiece set, Bortle slider, location, date. Defaults should
  give a useful result for a beginner who changes nothing but their location.
- **Location:** browser geolocation only when the user asks for it; otherwise typed or picked.
  Never store it.
- **Output:** a ranked list showing object, type, best time, altitude, eyepiece and verdict.
- **Per object:** tapping shows *why*: object vs sky brightness and the chosen eyepiece, with
  links to the relevant concept posts.
- **Share link:** settings in the URL, leaving out the exact location unless the user opts in.
- **Phones first:** people use this outdoors. Consider how it looks at night.
- **Attribution:** OpenNGC (CC-BY-SA-4.0) and a link to maglimit.

Post 11 introduces the tool: start with the question, show it working, explain the verdicts,
link back through the series, and be upfront that it's a model and eyes vary (±0.5 magnitude
or more).

## 7. Constraints

- The site is on Vercel Hobby, which is non-commercial, and ads stay off. A free tool is fine;
  check hosting terms before monetising anything around it.
- Everything runs in the browser from static files, so nothing here needs a server.
- If a change to the model seems necessary, raise it for the maglimit repo instead of changing
  only the TypeScript.
