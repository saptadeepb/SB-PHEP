# SB-PHEP-II — replication package

Exact stochastic bilevel optimisation of corridor electrification, charging
capacity and corridor pricing on port–hinterland corridors, with a carrier
coalition that chooses routes, traction, platoons and empty repositioning.

This package reproduces every number, table and figure in the manuscript
`paper/SB_PHEP.tex` from the raw input files in `data/`.

> During anonymised review, the manuscript sources and the scripts that build them
> (`paper/`, `make_numbers.py`, `check_manuscript.py`, `make_package.py`) are not
> published in this repository; everything under `src/`, `data/` and `outputs/` is.

## The question and the answer in one place

*When does electrifying port–hinterland trucking cut emissions?* The paper answers
it in general and then tests the answer on ten corridors serving the world's
busiest ports.

* **Theory (manuscript Section 3, proofs in the supplement).** A neutral grid
  factor `ef0 = φγ/ε` fixed by the two vehicles alone; a decomposition showing that
  the decisive factor is the *load-weighted* one (traction effect + plan effect);
  conditions under which it lies below the annual average; a lifetime condition
  with a critical grid-decarbonisation rate `g*`; a social break-even and the band
  outside which the first best never electrifies; a carbon-aligned charge with the
  tax-netting formula; second-best breakpoints for a state-blind charge; an
  a-posteriori welfare bound; haulage-cost neutrality on tree corridors; and a
  four-term variance decomposition of the threshold's measurement uncertainty.
* **Global atlas.** The 50 busiest container ports placed against the threshold on
  their published national grid factors (`data/atlas_ports.csv`).
* **Ten corridors.** Rotterdam (lead case), Antwerp, Shanghai, Ningbo, Qingdao,
  Tianjin, Shenzhen, San Pedro Bay, Jebel Ali and JNPT, in eight grid regions.
* **What is calibrated rather than observed, and how it is tested.** Inland
  freight splits: re-drawn 30 times from a Dirichlet around the population weights
  (`split_ensemble`). Haulage costs: halved and doubled on every corridor
  (`haulage_neutrality`), and proved not to change the verdict on tree corridors.
  Grid states: the published operating, build and combined margins are used where
  they exist (`data/grid_factor_sources.csv`); Section 3 shows that the results hold
  for any finite set of states.

## Run stages used for the manuscript

```bash
python3 -m src.run_all verdicts 900     # ten-corridor verdicts and decomposition
python3 -m src.run_all ensemble 300     # 30 re-drawn freight splits per corridor
python3 -m src.run_all collabx 900      # collaboration decomposition, all corridors
python3 -m src.run_all haulage 600      # haulage cost x0.5 and x2
python3 -m src.run_all lifetime 600     # lifetime threshold and g*
python3 -m src.run_all cross 600        # ten corridors x five families; regime matrix
python3 -m src.run_all validate 900     # correctness tests
python3 -m src.run_all main 900         # lead case: instruments, VSS, EVPI, sensitivity
python3 -m src.certify_focal 1800       # re-solve time-limited lead-case families
python3 -m src.run_all frontier 300
python3 -m src.run_all extras 600       # contingency, seeds, stability
python3 -m src.run_all scale 300
python3 -m src.run_all reachx 600       # reach on three more corridors
python3 -m src.run_all figures
```

## Quick start

```bash
pip install -r requirements.txt
python3 -m src.run_all            # full study: ~10 h on two cores
python3 make_numbers.py           # regenerate the manuscript's numeric macros
python3 make_interpretation.py    # regenerate outputs/RESULTS_INTERPRETATION.md
python3 check_manuscript.py       # audit the manuscript against the results
python3 make_package.py           # build the PDFs and the submission archive
```

`make_package.py` refuses to build the archive if `check_manuscript.py` fails, so
a package that ships is one whose numbers have been checked against the
computations.

Individual stages, if you would rather not run everything at once:

```bash
python3 -m src.run_all validate   # the six correctness tests
python3 -m src.run_all main       # focal corridor: instruments, VSS, collaboration, sensitivity
python3 -m src.run_all cross      # ten corridors, and the network x regime matrix
python3 -m src.run_all scale      # scalability of the exact methods
python3 -m src.run_all frontier   # reach and the cost-emissions frontier per instrument
python3 -m src.run_all extras     # state contingency, seed robustness, scenario stability
python3 -m src.run_all figures    # rebuild figures from existing CSVs
```

`extras` also splits into `contingency`, `seeds` and `stability`, and
`outputs/summary.json` is written under a lock and merged rather than replaced, so
independent stages can be run at the same time on a multi-core machine without
one discarding the other's results:

```bash
(python3 -m src.run_all frontier    && python3 -m src.run_all scale)     &
(python3 -m src.run_all contingency && python3 -m src.run_all seeds \
                                    && python3 -m src.run_all stability) &
wait && python3 -m src.run_all figures
```

## What is where

```
data/                       every input, with provenance
  DATA_SOURCES.md           what each number is, where it came from, when
  energy_regimes.csv        electricity and diesel prices, grid CO2 by country
  parameters.csv            vehicle technology, costs, carbon price, with ranges
  ports.csv                 container throughput, road share, circuity factor
  networks/*_nodes.csv      node coordinates, demand weights, import/export split
  networks/*_arcs.csv       physical links and whether they may be electrified

src/
  data_io.py                loaders; road distances derived from coordinates
  instance.py               builds an instance from the data files
  lp.py                     the lower-level LP, described symbolically
  bounds.py                 the provably valid dual and slack bounds
  models.py                 follower LP, centralized, strong-duality, KKT, enumeration
  cooperative_game.py       characteristic function, Shapley, core LP, gain decomposition
  experiments.py            the computational study
  scale.py                  instance-size controls for the scalability study
  validate.py               the six correctness tests
  figures.py                every manuscript figure
  figures_osm.py            the study-area map on OpenStreetMap or CartoDB
                            tiles, for anyone who wants a raster base
  run_all.py                driver

outputs/tables/*.csv        every result, one file per experiment
outputs/figures/*.pdf|png   every figure
outputs/summary.json        machine-readable headline numbers
paper/                      manuscript, supplementary material, response to
                            reviewers, bibliography, generated numbers.tex
paper/tables/*.tex          one file per table, \input by the document that
                            uses it
paper/figures/*.pdf|png     figures, copied from outputs/figures
make_numbers.py             results  ->  paper/numbers.tex
make_interpretation.py      results  ->  outputs/RESULTS_INTERPRETATION.md
check_manuscript.py         audits the manuscript against the results
make_package.py             builds the PDFs and the submission archive
```

## The study-area map

`figures.fig_study_areas` draws the corridors on the GSHHS shoreline and the
WDB political and river lines that ship with Basemap, so the figure needs no
network and no tile server and will render identically in ten years. Scale bars
are drawn from the ground distance at their own latitude rather than from
projected units, which is what Basemap's own `drawmapscale` does and what makes a
Mercator scale bar overstate distance by 1/cos(latitude) --- 61% at Rotterdam.
Place names are positioned by the measuring search in `_place_label`: every
candidate position is scored against the other labels, the markers, the scale bar
and the panel frame, a name is rejected outright if it would read as belonging to
a neighbouring node, and a leader line is drawn wherever a name has had to move.

`python3 -m src.figures_osm` redraws the same figure on OpenStreetMap Standard or
CartoDB tiles for anyone who prefers a raster base and has network access to
those servers; it writes the same file name, so the manuscript picks it up
without further change. It is not the default because a tile base cannot be
reproduced offline, and because the providers' terms and keys change.

## Reproducibility

The manuscript quotes **no literal result**. Data descriptions in the calibration
table carry their published values as text; every *computed* figure in the text is a macro
defined in `paper/numbers.tex`, which `make_numbers.py` writes from
`outputs/summary.json` and `outputs/tables/*.csv`. Sentences whose *direction*
could change with the calibration are generated too -- the interpretation of the
instrument comparison, of the stochastic measures, of the emission frontier, of
state contingency and of scenario stability -- so the manuscript cannot claim a
gap that is not there. `check_manuscript.py` closes the loop from the other side: it re-derives the paper's arithmetic from the input
data, checks that the ordering claims hold in the result files, and verifies that
every cross-reference, citation and figure resolves. It exits non-zero if
anything disagrees, so it can be run in CI.

The submission is two documents: `paper/SB_PHEP.tex` and
`paper/SB_PHEP_supplementary.tex`, which carries the notation, the full
calibration with its provenance, the proofs, the verification suite and the result
tables the manuscript summarises. **Each compiles on its own**, which is what a
journal system and most editors do: neither reads the other's `.aux`. The numbers
each needs from the other are generated — `make_numbers.py` reads both `.aux`
files and writes one macro per label into `numbers.tex` (`\xref...` for the
manuscript's sections, tables, figures, equations and results, `\xrefSup...` for
the supplement's), so a result that moves between the documents cannot leave a
stale number behind and nothing is numbered by hand. Every table is a separate
file under `paper/tables/`, `\input` by whichever document uses it.
`check_manuscript.py` fails the build if either document loads the other through
`xr`, if the manuscript hard-codes a supplement number, if an `\input` does not
resolve, if the supplement quotes an undefined macro, if a figure in either
document was never layout-audited, or if the manuscript exceeds its page budget.

`paper/response_to_reviewers.tex` is held to the same standard. It cannot `\ref`
into either document, so `make_numbers.py` reads both `.aux` files and emits one
`\xref...` macro per label (`\xrefSup...` for the supplement's); the letter uses
those, and `check_manuscript.py` fails if the letter hard-codes a section, table or
result number. `make_package.py` therefore compiles both documents, regenerates
`numbers.tex`, compiles them again, and only then builds the letter.

The only stochastic elements of an instance are the carrier market shares and the
node-level tilts, both drawn once from a fixed seed (20260909) and documented in
`data/DATA_SOURCES.md`. Everything else is deterministic, so runs are
bit-reproducible.

Two calibration properties are worth knowing before reading any result, because the
cross-country comparison rests on them and because both are easy to get wrong.

* **The scenario tree reproduces the published grid numbers.** Each corridor's three
  grid states are weighted so that the tree's *expected* emission factor equals the
  country's published annual average exactly, and the state price multipliers are
  scaled so the expected electricity price equals the published national price.
  Every instance records both realised means next to both published ones, and
  `check_manuscript.py` fails if any corridor's tree misses either. Without this, a
  cross-country statement is a statement about the construction.
* **The electric consumption figure is grid-side, not battery-side.** The published
  measurement excludes charging losses, so `e_elec` (battery) is divided by
  `charger_efficiency` to get the ε the model uses for the charging rows, the
  emissions, the surcharge and the capacity sizing. The emission-neutral threshold
  is computed on that grid-side figure.

## Solver

All models are linear or mixed-integer linear and are solved with HiGHS through
Pyomo. No heuristic or metaheuristic is used anywhere. Headline results are
certified at a zero MIP gap; the frontier and sensitivity sweeps use a `1e-4`
relative gap, which is why their central rows sit a few parts in `1e6` above the
headline table. Every result file carries a `status` and a `certified_mip_gap`
column, and every table in the manuscript that contains a time-limited row marks
it.

## The six correctness tests

| Test | What it checks |
|------|----------------|
| T1 | Fixing the leader at the optimum and re-solving each scenario's lower-level LP independently reproduces the embedded follower objective |
| T2 | The strong-duality and KKT/big-M reformulations — two independent encodings — return the same optimum |
| T3 | On an instance small enough to enumerate, brute force over every electrification pattern reproduces the optimum |
| T4 | Every analytically derived dual bound dominates the duals observed at a spread of leader decisions |
| T5 | First best ≤ every restricted instrument family, and every family ≤ no instrument at all |
| T6 | Imposing the closed-form charge levels of Theorem 2 reproduces the centralized optimum |

`check_manuscript.py` adds a further layer on top of these: it re-derives the
threshold arithmetic on the grid-side consumption figure, checks that each published
grid factor's position relative to the threshold interval matches the *generated*
sentence that reports it, checks that every family's proved emission floor lies at or
below what it demonstrably attains, checks that the regime matrix carries both the
full-regime and the grid-only swap, and checks that the response letter hard-codes no
section, table or result number of the manuscript.

Results that are incumbents rather than certified optima are marked as such: every
result file carries `status` and `certified_mip_gap` columns, and no claim in the
manuscript rests on an unproved infeasibility.

## Using your own data

Every input is a file, so pointing the model at a different corridor or a
different country means editing `data/`, not `src/`. A new corridor needs a
`*_nodes.csv` and a `*_arcs.csv` under `data/networks/` plus a row in
`data/ports.csv`; a new country needs a row in `data/energy_regimes.csv`. The
loaders check connectivity and will refuse a network whose demand nodes are not
reachable from the port.
