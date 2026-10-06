# SB-PHEP: electrification, pricing and carrier collaboration on port–hinterland corridors

This repository holds the replication package for the paper

> **When does electrifying port–hinterland trucking cut emissions? Grid emission factors, carbon-aligned corridor charges and carrier collaboration**
> (submitted to *Transport Policy*, 2026; under review)

It contains every input with its provenance, the model and solution code, every result file, and every figure. From these files you can reproduce each number, table and figure in the paper and its supplementary material.

## What the study asks

A port–hinterland corridor authority decides three things: which road links to equip for electric trucks, how much charging capacity to install, and how to charge for corridor use. A coalition of carriers then chooses its routes, electric or diesel traction, platoons and empty-container movements. Freight demand and grid carbon intensity are uncertain. The study is calibrated on public data for eight corridors in eight countries on four continents: Jawaharlal Nehru Port / Nhava Sheva (India, the focal case), Manzanillo (Mexico), Rotterdam (the Netherlands), Los Angeles (USA), Shanghai (China), Jebel Ali (UAE), Busan (South Korea) and Durban (South Africa). It answers three policy questions:

1. **When does electrification cut CO₂?** Only where the grid's emission factor is below a threshold set by the two vehicles' energy use. India's officially published emission factors straddle that threshold's central value, and the average grids of South Africa and China lie within its uncertainty band.
2. **How should the corridor be charged?** Charge diesel truck-kilometres, discount platooned trucks by exactly their energy saving, and add a charging surcharge indexed to the grid state. Toll waivers for platooned trucks over-reward platooning.
3. **What should carriers share?** Information about empty containers. On all eight corridors pooling delivers most of the collaboration gain; platooning delivers little.

## Quick start

```bash
pip install -r requirements.txt
python3 -m src.run_all            # full study: several hours on two cores
python3 make_interpretation.py    # plain-language note on the results -> outputs/RESULTS_INTERPRETATION.md
```

You can also run the stages one at a time:

```bash
python3 -m src.run_all validate   # the six correctness tests
python3 -m src.run_all main       # focal corridor: instruments, VSS, collaboration, sensitivity
python3 -m src.run_all cross      # eight corridors, and the corridor x national-regime matrix
python3 -m src.run_all collabx    # carrier-collaboration decomposition on every corridor
python3 -m src.run_all sens       # sensitivity sweep at zero optimality gap
python3 -m src.certify_focal 3600 # re-solve the focal restricted instruments with a longer limit
python3 -m src.run_all scale      # scalability of the exact methods
python3 -m src.run_all frontier   # reach and the cost-emissions frontier per instrument
python3 -m src.run_all extras     # state contingency, seed robustness, scenario stability
python3 -m src.run_all figures    # rebuild figures from existing CSVs
```

`outputs/` already holds the results reported in the paper, so you can inspect them without re-running anything.

## What is where

```
data/                       every input, with provenance
  DATA_SOURCES.md           what each number is, where it came from, when it was retrieved
  energy_regimes.csv        electricity and diesel prices, grid CO2 factors by country
  parameters.csv            vehicle technology, costs, carbon price, with low/central/high values
  ports.csv                 container throughput, road share, circuity factor
  networks/*_nodes.csv      node coordinates, demand weights, import/export split
  networks/*_arcs.csv       physical links and whether they may be electrified

src/
  data_io.py                loaders; road distances derived from coordinates
  instance.py               builds an instance from the data files
  lp.py                     the carriers' (lower-level) LP, described symbolically
  bounds.py                 the provably valid dual and slack bounds
  models.py                 follower LP, centralised, strong-duality, KKT/big-M, enumeration
  cooperative_game.py       characteristic function, Shapley value, core LP, gain decomposition
  corridors.py              the eight corridors, their countries and the focal case
  experiments.py            the computational study
  certify_focal.py          longer re-solve of the focal corridor's restricted instruments
  scale.py                  instance-size controls for the scalability study
  validate.py               the six correctness tests
  figures.py                every figure, including the policy-framework schematic
  figures_osm.py            optional study-area map on OpenStreetMap/CartoDB tiles
  run_all.py                driver

outputs/tables/*.csv        every result, one file per experiment
outputs/figures/*.pdf|png   every figure, with FIGURE_AUDIT.txt (layout checked by measurement)
outputs/summary.json        machine-readable headline numbers
outputs/RESULTS_INTERPRETATION.md   plain-language note generated from the results
make_interpretation.py      results -> outputs/RESULTS_INTERPRETATION.md
```

## Reproducibility

- **Deterministic runs.** The only stochastic inputs are the carrier market shares and the node-level tilts. Both are drawn once from a fixed seed (20260909) and documented in `data/DATA_SOURCES.md`, so runs are bit-reproducible.
- **The scenario tree reproduces the published national figures.** For each corridor, the expected grid emission factor of its tree equals the country's published annual average exactly. The same holds for the expected electricity price.
- **Electric consumption is measured on the grid side.** The published battery-side consumption is divided by the charging efficiency, and every emission, cost and threshold calculation uses this grid-side figure.
- **Solver.** All models are linear or mixed-integer linear and are solved with HiGHS through Pyomo. No heuristic is used. Headline results are certified at a zero MIP gap unless a run reached its time limit; every result file carries `status` and `certified_mip_gap` columns. The reach minimisations and frontier points use a `1e-3` relative gap. Away from the focal instrument comparison the state-contingent charge (F4) is evaluated through the paper's corollary that, at its closed-form levels, the leader–follower optimum equals the centralised optimum, so those rows are single MILPs solved to proven optimality. Where a time-limited run of a restricted family (F1–F3) returned a design worse than the uncharged one, the uncharged design, which belongs to every family's menu, is reported and marked `(F0 design retained)`.

## The six correctness tests

| Test | What it checks |
|------|----------------|
| T1 | Fixing the authority's decision at the optimum and re-solving each scenario's carrier LP independently reproduces the embedded follower objective |
| T2 | The strong-duality and KKT/big-M reformulations, two independent encodings, return the same optimum |
| T3 | On an instance small enough to enumerate, brute force over every electrification pattern reproduces the optimum |
| T4 | Every analytically derived dual bound dominates the duals observed at a spread of leader decisions |
| T5 | The first best is no worse than any restricted instrument family, and every family is no worse than no instrument at all |
| T6 | Imposing the closed-form first-best charge reproduces the centralised optimum |

## The study-area map

`figures.fig_study_areas` draws the eight corridors with Basemap, using its GSHHS shoreline and WDB boundaries. The figure therefore needs no network access or tile server. `python3 -m src.figures_osm` redraws it on OpenStreetMap or CartoDB tiles if you prefer a raster base.

## Using your own data

The instances are calibrated, not observed. Throughput, prices, emission factors and vehicle data are published figures. No public source reports how a corridor's volume splits across inland nodes and carriers, so that split is a documented, seeded rule. A corridor authority sizing a real programme should point the loaders in `src/data_io.py` at its own series. Every quantity enters as an input, not a hard-coded value.

## Contact

Saptadeep Biswas, GITAM School of Business, GITAM (Deemed to be University), Visakhapatnam, India · sbiswas3@gitam.edu · ORCID [0000-0002-2092-5487](https://orcid.org/0000-0002-2092-5487)
