# maglimit planner — design

**Status:** approved by Pratik on 2026-11-05. Written 2026-10-31 on top of the v0.1.0
modernization (PR #6), revised 2026-11-05 with Pratik's first round of answers. Everything
listed under "Decided" is settled; items marked **(decide)** are small and left open.

**Decided by Pratik (2026-11-05)**
- Users: all three groups — experienced observers at the eyepiece, beginners at outreach
  events, and students/educators.
- Interfaces: the CLI table is a must for basic use. The package must also work in
  notebooks, and eventually the tool lives on physicstuff.com as a UI, alongside posts
  explaining every term and concept it uses.
- Astrophotography comes later, after the visual planner.
- Blog and site work is handled in a separate session in the physicstuff.com repo, from the
  handoff file in `docs/superpowers/handoff/`.
- Website: a TypeScript port running in the browser, with the Python package as the source
  of truth and a shared conformance file keeping the two in agreement (§7).
- Catalogue: bundle OpenNGC in the package, with attribution and its own license file (§5.2).
- Ranking: `--goal easy` by default, `--goal challenge` as an option (§5.5).
- Moon in v1: report phase and separation and apply a simple penalty; the full
  sky-brightness model comes later (§5.3).

---

## 1. The idea in one paragraph

Turn maglimit from "is this one object brighter than my scope's limit?" into
**"what's worth pointing my telescope at tonight, from here, and how?"** You describe your
telescope, your eyepieces and how dark your sky is; maglimit returns a ranked list of
deep-sky objects that are up tonight, each with *when* it's best placed, *how hard* it will
be to see, and *which eyepiece* to use. It runs offline (bundled catalogue), from a one-line
CLI, Python or a notebook, and eventually as a public tool on physicstuff.com, where each
term it shows links to a post explaining it.

## 1a. Who it's for

| User | What they want | What that means for the tool |
|---|---|---|
| Experienced observer | A good list for tonight, including targets that stretch their scope | Full numbers via `explain()`, challenge ranking, own eyepieces and SQM reading |
| Beginner at an outreach event | "What can I show people right now that won't disappoint?" | Plain verdicts, easiest-first ranking, sensible defaults, few required inputs |
| Student / educator | To understand *why* an object is or isn't visible | Every verdict explainable; sliders in notebooks and on the site; linked concept posts |

The same engine serves all three; they differ in defaults and how much detail is shown.
This overlaps closely with the audience in physicstuff's `PRODUCT.md` (curious non-experts,
students, educators), which is part of why the site is a natural home for it.

## 2. Why this is worth building

- **The current check is misleading for the targets people care about.** maglimit compares
  an object's *total* magnitude with the scope's star-limit. That works for stars and small
  bright objects, but galaxies and nebulae spread their light out. M31 is magnitude ~3.4–4.4
  yet the whole object is ~3° across; most faint galaxies that pass the current test are
  invisible in practice, and some large "bright" nebulae are invisible from a city at any
  aperture. The deciding quantity is **surface brightness against the sky background**.
- **Sky darkness is missing entirely.** The same 200 mm scope behaves like two different
  instruments in a Bortle 3 and a Bortle 7 sky.
- **The gap in the tooling:** apps like Stellarium, SkySafari, Telescopius and AstroPlanner
  do planning well, but (as far as I know) there is no small, open, pip-installable library
  that gives a *physically modelled* "can I see it with this scope under this sky" answer
  that people can script, test and cite. astroplan covers *when* things are up, not
  *whether you can see them*. That combination is maglimit's niche.
- It builds on what exists (Telescope, limiting magnitude, catalogue lookup) instead of
  starting over, and the Zenodo DOI and docs make it citable for outreach/education use.

## 3. Goals, non-goals, anti-goals

**Goals**
1. Rank catalogue objects by how *visible* they are for a given telescope + sky + observer.
2. Account for when objects are up: altitude, darkness (astronomical twilight), Moon.
3. Recommend magnification/eyepiece per object from the user's own eyepieces.
4. Work offline after install; a network catalogue (NED) stays optional.
5. Usable as a CLI table first, then Python API and notebook, then a UI on physicstuff.com.
6. Explainable: every verdict can show its numbers (object SB, sky SB, threshold, margin).
7. Results available as plain data (`to_dict()` / JSON with a stable shape), so the notebook,
   the site and tests all read the same thing.

**Non-goals (for now)**
- Planetarium rendering / star charts.
- Telescope control (GoTo, INDI/ASCOM).
- Solar-system planning beyond "the Moon is a nuisance" (planets/comets later, maybe).
- Astrophotography exposure planning — decided: later, after the visual planner; see §11.

**Anti-goals** (would make it a failure even if it runs)
- **Confident wrong answers.** A "visible" verdict for something nobody could see with that
  setup is worse than no tool. Output must be graded ("easy / challenging / very hard /
  not visible") with uncertainty, not a bare True/False.
- Requiring an account, API key or internet connection to answer "what's up tonight".
- Breaking the existing v0.1 API (`Telescope`, `is_object_observable`, `smallest_scope`).

## 4. What a user sees

### CLI

```bash
maglimit tonight --aperture 200 --fstop 5 --eyepieces 32,25,10 \
    --lat 18.5 --lon 73.9 --bortle 5 --limit 15
```

Illustrative output (numbers made up for the layout):

```
Tonight (2026-11-01), Bortle 5 (SQM ~20.0), dark from 19:52 to 05:10
200 mm f/5 — star limit ~13.4

 #  Object   Type       Mag   Size     Best     Alt  Eyepiece  Verdict
 1  M42      Neb        4.0   85'x60'  03:10    52°  32 mm 31x  easy
 2  M31      Galaxy     3.4   178'x70' 20:40    61°  32 mm 31x  easy (core only)
 3  M57      PN         8.8   1.3'     19:55    38°  10 mm 100x easy
 4  NGC 891  Galaxy    10.0   13'x2'   21:30    70°  10 mm 100x very hard
 ...
Not shown: 42 objects up but below threshold (use --show-hidden)
```

Other commands (small, cheap to add once the core exists):
- `maglimit check M33 ...` — one object, full explanation of the verdict.
- `maglimit scope --aperture 200 --fstop 5 --eyepieces 32,25,10` — scope summary: star
  limit, resolution, magnification / exit pupil / true field per eyepiece, max useful mag.

### Python

```python
import maglimit as ml

scope = ml.Telescope(aperture=200, fstop=5, eyepieces=[32, 25, 10])
site = ml.Site(lat=18.5, lon=73.9, bortle=5)          # or sqm=20.1
plan = ml.tonight(scope, site, date="2026-11-01", types=["galaxy", "pn"], limit=20)

plan                 # astropy QTable, nice repr in notebooks
plan.to_pandas()     # if pandas is installed
ml.explain("NGC 891", scope, site)   # the numbers behind one verdict
```

### Notebook

`plan` displays as a formatted table through `_repr_html_`. An optional extra
(`maglimit[notebook]`, ipywidgets) adds aperture / Bortle sliders that re-rank the list live,
which doubles as a teaching demo and a prototype of the website UI.

**(decide)** CLI and Python units: mm for aperture/eyepieces (as today), degrees for
lat/lon, local time zone guessed from the system with `--tz` to override.

## 5. How it works

```
 catalogue ──► filter by sky position / date ──► visibility model ──► rank ──► table / CLI
 (OpenNGC,      (altitude, darkness window,       (per object, per          (score, best time,
  bundled)       Moon separation)                  eyepiece)                 verdict, eyepiece)
```

### 5.1 Inputs

| Thing | Fields | Notes |
|---|---|---|
| `Telescope` | aperture, fstop (or focal length), eyepieces (focal length + apparent FOV), central obstruction, transmission | extends the existing class; new fields optional with sensible defaults (obstruction 0, transmission 0.8, AFOV 52°) |
| `Site` | lat, lon, elevation, sky darkness as `bortle` *or* `sqm` | Bortle mapped to a typical SQM value; SQM wins if both given |
| `Observer` | eye pupil (default 7 mm, or from age), experience factor | optional; experience is a small magnitude offset |
| date / time window | default: tonight, astronomical dusk → dawn | |

### 5.2 Catalogue (offline)

- Bundle **OpenNGC** (NGC + IC + its addendum, which covers the non-NGC Messiers like
  M40/M45): ~14k objects with type, RA/Dec, major/minor axis (arcmin), B and V magnitude,
  galaxy surface brightness, Messier number and common names.
- Ship a trimmed copy (only the columns we use, ~1 MB) inside the wheel, with a script in
  the repo to regenerate it from upstream.
- Name lookup accepts `M31`, `NGC 224`, `NGC224`, `Andromeda Galaxy`.
- Missing data is common (many objects have B but no V, no minor axis, etc.). The model
  needs explicit fallback rules (e.g. V ≈ B − 0.8 for galaxies, round object if no minor
  axis) and a flag in the output when a fallback was used.
- NED stays available as an optional live lookup for objects outside the catalogue.
- OpenNGC is **CC-BY-SA-4.0** while maglimit is MIT. Decided: bundle it with clear
  attribution and a separate license file. The data file stays CC-BY-SA (share-alike applies
  to the data, not our code).

### 5.3 Where and when (ephemeris)

Plain **astropy** (`EarthLocation`, `AltAz`, `get_sun`, `get_body("moon")`) — no extra
dependency; astroplan is an option but not needed for this.

- Darkness window: Sun below −18° (astronomical twilight), configurable.
- Sample the window every ~10 min; per object take max altitude and the time it occurs.
- Minimum useful altitude default 20° (configurable; horizon-limited sites).
- Atmospheric extinction: dim the object by `k · airmass` (k ≈ 0.25 mag/airmass in V, by
  site elevation later). This matters a lot for low southern/northern targets.
- Moon: v1 just reports illumination and separation and penalises objects close to a bright
  Moon. v2 can add a proper moonlit-sky brightness model (Krisciunas & Schaefer 1991) that
  raises the sky background per object.
- IERS: configure astropy so it never blocks on downloading Earth-orientation data —
  minute-level accuracy is plenty here, and this keeps "offline" true.

### 5.4 The visibility model (the core)

Two cases, because stars and extended objects are seen differently.

**a) Point-like objects** (stars, small planetaries, compact clusters, galaxy cores):
compare magnitude with a **sky-aware telescopic limiting magnitude**.
- Naked-eye limit from sky brightness: `NELM ≈ 7.93 − 5·log10(10^(4.316 − SQM/5) + 1)`
  (an approximation widely used with SQM readings; ≈ 6.6 at SQM 22, ≈ 4.0 at SQM 18).
- Telescopic limit following Schaefer (1990): gain from aperture, transmission and
  obstruction, plus the extra gain from higher magnification darkening the sky background.
- Keep `lim_mag()` (2 + 5·log₁₀ D) unchanged for backward compatibility; add
  `lim_mag(site=...)` or a new method for the sky-aware value. **(decide)** name.

**b) Extended objects** (galaxies, nebulae, large clusters): contrast detection.
- Object **surface brightness**: `SB = m + 2.5·log10(area in arcsec²)`, area = π/4·a·b.
  Example: M31 with B 4.29 over 178′×70′ → ~23.1 mag/arcsec² averaged over the whole disk,
  i.e. barely brighter than a dark sky (~22) — which is why you see the core, not "the
  galaxy". (A core/disk split for galaxies is a v2 refinement.)
- In the eyepiece, both the object and the sky background are dimmed by the same factor
  (set by exit pupil vs eye pupil), so **contrast is fixed, but brightness and apparent size
  change with magnification** — and the eye's detection threshold depends on both.
- Use the **Blackwell (1946) contrast-threshold data** as used by Roger Clark (*Visual
  Astronomy of the Deep Sky*, 1990): for each eyepiece, compute background brightness and
  the object's apparent size, look up the threshold contrast, and compare with the object's
  actual contrast. The margin (in log-contrast) is the visibility score.
- The eyepiece with the best margin is the **recommended eyepiece** — a genuinely useful
  output that no simple magnitude test can give.
- Clark's book is out of print but the model is published in his articles and widely
  re-implemented; we'd implement it from the published threshold tables, cite them, and keep
  the tables as data so they can be swapped.

**c) From margin to verdict.** Map the margin to `easy / moderate / challenging /
very hard / not visible`, with thresholds calibrated against real observing reports
(§9). The verdict, not the raw number, is what the CLI shows.

### 5.5 Ranking

Default score = visibility margin, lightly weighted by altitude and by object "interest"
(Messier/Caldwell/Herschel 400 membership, size). With three kinds of user, this is a flag
rather than one fixed order: `--goal easy` (default, suits beginners and outreach) and
`--goal challenge` (best target you can still just see).

## 6. Package layout (proposed)

```
maglimit/
  __init__.py          public API
  limiting_mag.py      existing v0.1 functions (kept, thin wrappers over the new code)
  telescope.py         Telescope, Eyepiece (optics: exit pupil, TFOV, max mag, Dawes)
  site.py              Site, Bortle↔SQM, NELM
  catalogue.py         load bundled OpenNGC, name lookup, fallbacks
  ephemeris.py         darkness window, altitude/airmass sampling, Moon
  visibility.py        point-source and extended-object models, verdicts
  planner.py           tonight(), explain()
  cli.py               `maglimit` command (argparse; no extra dependency)
  data/
    openngc.csv        trimmed catalogue + LICENSE-OpenNGC
    blackwell.csv      contrast-threshold table
scripts/
  build_catalogue.py   regenerate data/openngc.csv from upstream
```

Dependencies stay numpy + astropy (+ astroquery only for the optional NED lookup —
**(decide)** whether to make it an optional extra `maglimit[ned]`).

## 7. physicstuff.com integration

### What the site looks like today

Next.js 14 with static pages on Vercel (Hobby plan), TypeScript, MDX + KaTeX, and canvas
simulations. Each interactive follows a pattern: a maths engine in `src/lib/simulations/`
(with vitest tests), a React component in `src/components/simulations/` and an MDX article in
`src/content/<subject>/`, listed in `/lab`. There is no Python and no backend for
simulations, and `astrophysics` and `optics` subjects already exist.

### How the tool should run on the site

| Option | Pros | Cons |
|---|---|---|
| **A. TypeScript port of the model, in the browser** (chosen) | Fits the existing pattern exactly; static, no server to run or pay for; instant slider response; works on phones | Two implementations to keep in agreement |
| B. Python API (Vercel function or Render) | One implementation | astropy is a heavy function bundle, cold starts, a server to maintain and rate-limit; sliders feel slow |
| C. Python in the browser (Pyodide) | One implementation, no server | Tens of MB to download before anything works; poor on phones, which is what people have outdoors |

**Decided: A, with Python as the source of truth.** The maths that needs porting is
small: optics formulas, surface brightness, a table lookup for the contrast threshold, and
altitude/airmass. Sun and Moon positions can come from a small library such as
`astronomy-engine` rather than being hand-written.

Keeping the two in agreement is what makes this safe:
- maglimit publishes **shared data files**: trimmed catalogue JSON, the threshold table, and
  a **conformance file** of inputs and expected outputs generated by the Python code.
- The site's vitest suite runs that conformance file against the TypeScript engine, so a
  mismatch fails its tests. The website can't silently disagree with the package.
- A `scripts/export_web_data.py` here produces those files; they get copied or synced into
  the site repo (`data/` or `public/`).

This also adds a design rule for the package: **keep the visibility model small, pure and
table-driven** (plain numbers in, plain numbers out, no astropy objects inside it). Astropy
stays at the edges for ephemeris and units.

Size budget: a full trimmed catalogue is about 1 MB before compression. The site could load
Messier + Caldwell + the brightest NGC/IC objects first (a few hundred KB or less) and fetch
the rest on demand. It loads as a static file, so there are no server costs.

### The UI

Fits the 3-file pattern and PRODUCT.md's "layman → simulation → derivation" contract, drawn
with the site's own components (`SimulationLayout`, `ParamSlider`, four-ink palette):
- Inputs: aperture, f-ratio, eyepiece set, Bortle slider, location (browser geolocation only
  on request, otherwise typed or picked; never stored), date.
- Output: the ranked list with plain verdicts; tapping an object shows *why* (object vs sky
  brightness, the chosen eyepiece) with links to the matching concept posts.
- Share link: settings in the URL, without the exact location unless the user opts in.

Worth its own page rather than one article's embed: e.g. `/lab/what-can-i-see`, or
`/astrophysics/what-can-i-see-tonight`. **(decide)**

### Post series and site work

The concept post series and everything the site needs to build the tool are in
[the physicstuff handoff](../handoff/physicstuff-what-can-i-see.md). A separate session in the
physicstuff.com repo handles that work. This repo's job is to supply the package and the
data files from 0.6 onward.

### Constraints from the site

- Vercel Hobby is non-commercial and ads stay off. A free tool is fine; anything monetised
  around it needs a hosting check first.
- OpenNGC attribution (CC-BY-SA-4.0) must also appear on the tool page, and the catalogue JSON
  stays under that license.
- If the tool goes public, wrong verdicts reach beginners, so the §9 golden cases must pass in
  both implementations before launch.

## 8. Phasing

| Release | Scope | Done when |
|---|---|---|
| **0.2 – optics & sky** | `Eyepiece`, exit pupil, TFOV, max useful magnification, Dawes limit; `Site` with Bortle/SQM → NELM; sky-aware star limit | `maglimit scope ...` prints a correct scope summary |
| **0.3 – catalogue & visibility** | bundled OpenNGC, name lookup, surface brightness, Clark/Blackwell model, `explain()` | `maglimit check M33 --bortle 7` gives a sensible graded verdict with numbers |
| **0.4 – tonight** | ephemeris, darkness window, extinction, Moon penalty, ranking, `tonight()` + CLI | `maglimit tonight ...` ranks a believable list in < 2 s |
| **0.5 – notebook & data** | `_repr_html_`, `to_dict()`/JSON, `maglimit[notebook]` sliders, tutorial rewrite, docs on the model | a notebook re-ranks live; every printed number is documented |
| **0.6 – web export** | `export_web_data.py`: catalogue JSON, threshold table, conformance file | the files validate against the schema and regenerate cleanly |
| **site** | TypeScript engine + vitest conformance, React tool, launch post | the site gives the same answers as the package on every conformance case |
| later | Moon sky-brightness model, observing lists (Messier marathon, H400), astrophotography, planets/comets | see §11 |

Each release is small enough to publish to PyPI on its own via the new release workflow.
Concept posts 1–6 (see the handoff) don't need the tool, so they can start any time.

## 9. How we'll know it's right

- **Unit tests** for optics formulas and SB/NELM conversions against hand-worked values.
- **Golden cases** — a table of "with X mm under Bortle Y, object Z is easy / hard / not
  visible", taken from published observing guides and logs (e.g. well-known city-vs-dark-site
  examples: M33 and M101 vanish from bright suburbs; M57 and M13 survive). The model must
  get these right; it's the guard against the "confident wrong answer" anti-goal.
- **Property tests**: more aperture never makes something less visible; darker sky never
  makes something less visible; higher altitude never hurts.
- **Cross-language conformance**: the same cases run against the TypeScript engine (§7).
- Performance: full catalogue × ~60 time samples should run in a couple of seconds
  (vectorised astropy, no per-object Python loops).

## 10. Risks

- **Model calibration** is the hard part and the real value. The Blackwell/Clark approach
  is well established but individual eyes vary by ±0.5 mag or more; we should present
  ranges, not precise predictions.
- **Catalogue data quality** (inconsistent magnitudes between sources, as in M31: V 3.44 in
  OpenNGC vs 4.36 from NED). Prefer V, fall back to B with a colour correction, flag it.
- **Two implementations drifting apart.** The conformance file in §7 is the guard.
- **Scope creep** toward a full planetarium. The non-goals in §3 are the guard.

## 11. Bigger possibilities (after the core)

- **Astrophotography mode (decided: later):** camera + scope → image scale, sampling vs seeing, field of
  view framing, rough exposure for a target SNR. Different model, same catalogue/ephemeris.
- **Observing lists & logs:** Messier marathon planner, Herschel 400 progress, export to
  SkySafari/Stellarium observing-list formats.
- **Light-pollution lookup:** pick SQM from a light-pollution map by lat/lon instead of
  asking for Bortle (needs a data source with a suitable license).
- **Teaching material:** classroom worksheets built from the post series and notebook.

## 12. Open questions

1. Where the tool lives on the site, and whether the post list in the handoff is complete.
   This can wait until the website work starts.

Smaller **(decide)** items remain in §4 (units and time zone), §5.4 (name of the sky-aware
limit) and §6 (NED as an optional extra); these can be settled during implementation.
