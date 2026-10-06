# Data provenance for SB-PHEP-II

Every number the model consumes is listed here with the publication it comes
from and the date it was retrieved. The list is deliberately explicit about
which quantities are **published measurements**, which are **published
aggregates we transform**, and which are **transparent allocation rules** that
stand in for information no public source reports at the resolution the model
needs. Nothing in the model is a number without a row in this file.

All monetary values are in **United States dollars**. Local-currency figures and
the exchange rate used to convert them are given in `energy_regimes.csv` so that
the conversion can be redone.

Retrieval date for every web source below: **9 September 2026**.

---

## 1. Grid carbon intensity

| Country | Clean state | Average | Marginal state | Basis |
|---|---|---|---|---|
| India | 0.512 | 0.710 | 0.961 | CEA v21.0, generation busbar, operational CO2 |
| Chile | 0.045 | 0.289 | 0.820 | Ember average (operational); outer states IPCC AR5 lifecycle |
| Mexico | 0.060 | 0.474 | 0.490 | Ember average (operational); outer states IPCC AR5 lifecycle |
| Netherlands | 0.030 | 0.254 | 0.490 | Ember average (operational); outer states IPCC AR5 lifecycle |

Units are kg CO2 per kWh **at the generation busbar**. Transmission and
distribution losses are *not* added, and the diesel factor used against them is
tank-to-wheel, so both sides of the comparison exclude their upstream chains.
That is a deliberate and symmetric choice, but it is a choice: the sensitivity
section of the paper reports the alternative boundary, in which the grid factor is
grossed up by each country's T&D losses and diesel is taken well-to-wheel, and the
threshold table reports where every factor sits under both boundaries. The
alternative
moves the threshold but not the ordering of the countries.

**India is the only country for which all three states are published**, and this
matters for the paper's central result. CEA v21.0 reports, for FY 2024-25, a
weighted-average grid emission factor of **0.710 tCO2/MWh**, a CDM **simple
operating margin of 0.961** and a **build margin of 0.512**. We map the build
margin to the "clean" state, the weighted average to the "average" state and the
operating margin to the "marginal" state. **That mapping is our interpretation,
not the CEA's.** The CDM operating margin is the generation-weighted average of
all non-must-run plant, not a short-run marginal factor for a particular hour,
and the build margin is the intensity of recent capacity additions, not a
renewable-rich hour. What makes the mapping defensible is direction rather than
identity: incremental load is served by dispatchable plant, whose intensity the
operating margin measures, and new capacity is what eventually serves it. What
makes it worth stating clearly is that the paper's headline turns on the
distance between two of these numbers.

Ember's operational figure for India is **0.670**, about 6% below the CEA
weighted average we use. India's "average" therefore sits on a slightly
different basis from the other three rows, which are Ember throughout. We use
CEA for India because it is the only source that publishes the margins.

For the other three countries no equivalent national margin series is published,
so the average is Ember's figure for the **2025 data year** (the vintage matters:
Chile's 2024 figure is 0.260 against the 0.289 used here) and the marginal state is
the IPCC AR5
**lifecycle** median of the technology that sets the margin (coal at 0.820 for
Chile, combined-cycle gas at 0.490 for Mexico and the Netherlands). The clean state
is a renewable-rich hour. **These outer states are constructed, not published; they
sit on a lifecycle boundary while the average sits on an operational one; and they
are the least authoritative numbers in the study.**

Two further candours about the outer states. Mexico's *published* average and its
constructed marginal differ by only 3 %, so on published data Mexico has almost no
marginal signal; what the model actually uses is its 0.060 clean state against its
0.490 marginal state, an eight-fold spread that is a property of the construction
and not of the Mexican system. And the clean states for Mexico (0.060) and Chile
(0.045) are below anything those systems reach in practice: both are majority
fossil, with annual means of 0.474 and 0.289 respectively. They should be read as
the cleanest hour a corridor operator could *choose* to charge in under a future
mix, not as an observed hour today.

### How the states are weighted, and why

The weighting is easy to get wrong, so it is worth setting out. Take two states
(clean and marginal) with fixed probabilities: the expected grid factor of such a
tree reproduces no published number -- on this data Chile would come out 39 %
dirtier than its published annual average and Mexico 45 % cleaner than its own.
Every cross-country statement would then be a statement about the construction
rather than about the country, and the one published, measured grid number per
country -- the annual average -- would play no part in any computation.

The tree is therefore built so that **the expected emission factor equals the published
annual average exactly**, for every country. All three states are used. Mass `w`
is placed on the two outer states together (`OUTER_MASS = 0.50` in
`src/instance.py`) and the remainder on the published average; the split *within*
the outer pair is then solved rather than chosen:

    p_clean + p_marginal = w,
    p_clean * ef_clean + p_marginal * ef_marginal = w * ef_average
    =>  p_clean = w (ef_average - ef_marginal) / (ef_clean - ef_marginal)

which lies in [0, w] because the average lies between the two. The same scaling is
applied to the electricity-price multipliers, so that the expected electricity
price is the published national price rather than, as before, about 15 % above it.
The resulting probabilities and multipliers, and the realised expected factor and
price against the published ones, are recorded in every instance's metadata and in
`outputs/summary.json`, so the calibration can be checked without rerunning
anything. `OUTER_MASS` and the relative price and headroom spreads in
`GRID_STATES` remain modelling choices; what is no longer a choice is the mean.

## 2. Energy and fuel prices

| Country | Business electricity (USD/kWh) | Diesel (USD/L) | Diesel, local | Snapshot |
|---|---|---|---|---|
| India | 0.122 | 1.060 | INR 90.58-103.82 /L | GlobalPetrolPrices 9 Mar 2026; Indian metro retail 9 Sep 2026 |
| Chile | 0.169 | 1.050 | CLP 937.33 /L | GlobalPetrolPrices 9 Mar 2026 |
| Mexico | 0.213 | 1.470 | MXN 26.23 /L | GlobalPetrolPrices 12 Jan 2026 |
| Netherlands | 0.220 | 2.170 | EUR 1.82 /L | GlobalPetrolPrices 9 Feb 2026 |

Electricity prices are GlobalPetrolPrices' business/industrial series from its
international comparison table, which the source recommends over a single-quarter
snapshot because it removes quarter-to-quarter volatility. The four values are on
a common basis, which is what the cross-country comparison needs. Note that the
source's own India country page quotes 0.116 USD/kWh for June 2025, about 5%
below the comparison-table value used here; the difference is well inside the
sensitivity range. The diesel snapshots are on different
dates because the source updates countries on different cycles; the dates are
recorded per country in `energy_regimes.csv` and the spread between them is well
inside the sensitivity range reported in the paper.

For India the retail diesel price on the day of writing ranged from INR 97.83
(Mumbai) to INR 103.82 (Hyderabad, the metro nearest the focal corridor); we use
USD 1.06/L, corresponding to about INR 98/L at the stated exchange rate.

Within a scenario, the electricity price is the national business price
multiplied by a state factor (0.80 clean, 1.00 average, 1.55 marginal) that
represents the intraday spread between renewable-rich and scarcity-priced hours.
The multipliers are **calibrated, not published**, and are varied in the
sensitivity analysis.

## 3. Vehicle technology

| Quantity | Value | Range tested | Source |
|---|---|---|---|
| Electric traction energy, **at the battery** | 1.25 kWh/km | 1.15-1.45 | Le Corguille, Hacker and Dolinga (2025), *Real-world data analysis of battery electric trucks operating in Germany*, EVS38: 19 vehicles, **807 driving events, Sept 2023 - Jan 2025**, fleet mean **0.96 kWh/km at a mean gross combination weight of 20.4 t** over an 11-40 t range, rising **0.18 kWh/km per additional 10 t**, measured at the vehicle and **excluding charging losses** |
| Charging efficiency, grid to battery | 0.92 | 0.88-0.95 | AC and DC fast charging including rectifier and battery-side losses |
| **Electric energy drawn from the charger** | **1.36 kWh/km** | **1.21-1.65** | the two rows above, combined: this is the epsilon the model uses |
| Diesel fuel consumption | 0.340 L/km | 0.300-0.380 | Heavy tractor-semitrailer motorway consumption of 30-38 L/100 km (EcoTransIT World Methodology Update 2024; ICCT heavy-duty fleet data) |
| Platooning energy saving | 5.5 % | 3-7 % | NACFE *Confidence Report: Two-Truck Platooning* |
| Platoonable share of trucks | 0.75 | 0.50-0.95 | NACFE, as below |
| Diesel CO2 | 2.68 kg/L | 2.64-2.70 | Tank-to-wheel combustion factor for automotive diesel |

**The electric consumption figure is derived, and the derivation is stated in
full because the paper's central threshold depends on it.** Two independent
anchors are available at the 40 t gross weight of a container tractor-semitrailer
and we use both rather than picking the more convenient one.

*Anchor (a): the study's own regression.* The fleet mean of 0.96 kWh/km is for
vehicles of 11-40 t with a mean gross combination weight of 20.4 t. Applying the
study's published weight gradient,

    0.96 + 0.18 x (40 - 20.4) / 10  =  1.31 kWh/km.

40 t is inside the observed weight range but well above its mean, so this is an
extrapolation within the sample's support rather than a measurement at 40 t.

*Anchor (b): the study's own long-haul reference case.* The same report cites a
38 t tractor-semitrailer measured at **1.15 kWh/km over a 4,439 km journey**.
Adjusted to 40 t by the same gradient: 1.19 kWh/km.

We take **1.25 kWh/km**, between the two anchors, with a range of **1.15-1.45**
spanning the lower anchor to the regression value plus its own residual spread. We
deliberately offer no weight interpretation of that range: by the gradient it would
correspond to roughly 31 t to 48 t, which is not the uncertainty being represented.
The range spans the two anchors, not a weight band.

**The figure is battery-side and the model needs grid-side.** The measurement is
taken at the vehicle and excludes charging losses, but everything downstream in
the model -- the charging-capacity rows, the emission accounting, the per-kWh
surcharge and the grid-stress term -- is about energy *metered at the corridor's
chargers*. Using the battery figure throughout would understate grid draw, CO2,
charging-capacity requirement and charge revenue by the charging loss, all in the
direction that favours electrification. The model therefore uses `e_elec / charger_efficiency = 1.25 / 0.92 = 1.36 kWh/km`, and the
interval for the threshold is computed on the grid-side range 1.21-1.65.

Two pitfalls are worth naming, because together they move the threshold by about
15 %: taking a consumption figure below either anchor (1.10 kWh/km, say, which
neither supports), and omitting the charging loss. On the values above the
emission-neutral grid intensity is **0.67** kg CO2/kWh with an interval of
**0.48-0.85**. Because the sign of the Indian result depends on where
that threshold falls, the paper reports it as an interval over the full ranges of
all three inputs rather than as a point, and the verdict for each published grid
factor -- above the interval, below it, or inside it -- is generated from the data
rather than asserted in the text.

**The platooning figures are split between two parameters on purpose.** NACFE
measures a two-truck track average of about 7% at a 40-50 ft gap and then
recommends a derate of roughly one quarter for congestion, terrain and weather,
arriving at a real-world figure of about 4% across both trucks. Part of that
derate is about the saving itself and part is about how much of the running time
is actually spent in a platoon. We put the first part in the saving
(7% -> 5.5%) and the second in the platoonable-share cap (0.75), so that the
model's effective fleet-wide saving, 5.5% x 0.75 = 4.1%, reproduces NACFE's
headline number while keeping the two mechanisms separable. The upper bound of
the saving range, 7%, is the un-derated track figure; the 10% sometimes quoted is
the *following* truck alone and is not attainable as a two-truck average.

Note that the **efficiency ratio matters more than either number**: a diesel
truck burns 0.34 L/km, about 3.4 kWh of fuel energy, to do what an electric truck
does with 1.36 kWh of metered grid energy. Comparing grid and diesel emission factors *per kWh* without
that ratio is a unit error, and it reverses the sign of the electrification
result. The paper makes the comparison per kilometre throughout.

## 4. Carbon price

USD 190 per tonne CO2 (0.19 USD/kg), the US EPA (2023) *Report on the Social Cost
of Greenhouse Gases* central estimate for 2020 emissions at a 2 % near-term
Ramsey discount rate.

**Base-year caveat, stated because it matters for one conclusion.** EPA's table is
in **2020 dollars**, while the prices, wages and capital costs in this package are
2025-26 figures. We do not rebase the SCC, because doing so would require choosing
a deflator that EPA does not publish with the estimate, and because the paper's
claims are stated against a swept range rather than a point value. The direction
of the inconsistency should nevertheless be clear: on a consistent 2026-dollar
basis the central SCC would be *higher* than 0.19 USD/kg, which moves it closer to
the carbon price at which the Indian social ranking flips. The sensitivity sweep
runs to 0.80 USD/kg, well past any plausible rebasing, so the conclusion is
bracketed either way; but a reader comparing 190 with the flip price directly
should know the two are not in the same dollars. The 0.12-0.34 USD/kg range used in the sensitivity analysis
is the EPA's own 2.5 % and 1.5 % rate estimates (USD 120 and USD 340 per tonne)
from the same table. The sensitivity sweep in the paper additionally runs down to
zero and up to 0.80 USD/kg, well outside the EPA range. The paper also reports the
carbon price at which each qualitative conclusion changes, so a reader who prefers a
different valuation can locate their own position.

## 5. Corridors and road distances

Node coordinates are published WGS84 positions of the port and of the hinterland
towns. Arc lengths are **derived** unless a published road distance is supplied:
by default an arc is the great-circle distance between its endpoints multiplied
by a per-corridor circuity factor. Where a published driving distance is known,
it goes in the `road_km` column of the arcs file and overrides the derived value.

**The circuity factor is fitted, not validated.** It is chosen, one per corridor,
so that the derived length of a single reference route matches the published
driving distance for that route. Reporting that it then reproduces that distance
would be circular, so what the table below reports is the residual deviation on
the reference route and, more usefully, the fact that individual arcs can be much
further out.

| Corridor | Circuity | Reference route | Derived | Published | Deviation |
|---|---|---|---|---|---|
| Visakhapatnam | 1.12 | Port to Vizianagaram, NH-16 | 59.2 km | ~60 km | -1.3 % |
| San Antonio | 1.10 | Port to Santiago, Ruta 78 | 115.8 km | 104.6 km | +10.7 % |
| Manzanillo | 1.35 | Port to Guadalajara, MEX-54D | 311.5 km | ~310 km | +0.5 % |
| Rotterdam | 1.12 | Maasvlakte to Venlo, A15/A16/A58/A67 | 187.0 km | ~180 km | +3.9 % |

Individual arcs are worse, and the failures are **patterned, not random**: the
fitted factor understates port-access and mountain legs and overstates flat
motorway legs. Three arcs are far enough out to carry their own `road_km` value
rather than the fitted rule:

| Arc | Great circle | Fitted rule | Published road | Implied circuity |
|---|---|---|---|---|
| Venlo to Duisburg (A67/A40) | 41.5 km | 46.5 km | **75 km** | 1.8 |
| Vizianagaram to Jeypore (NH-26, Eastern Ghats) | 120.4 km | 134.8 km | **169 km** | 1.40 |
| Narsipatnam to Jeypore (NH-326, Eastern Ghats) | 132.4 km | 148.2 km | *none located* | 1.40 assumed |

The third row is the weakest arc length in the package and is labelled as such in
the arcs file: no published road distance could be found for it, so the circuity
observed on the adjacent Ghats arc (1.40) is applied locally instead of the
corridor-wide 1.12. A consistency check on the corrected Visakhapatnam network:
port to Jeypore via Anandapuram and Vizianagaram now totals 228 km against a
published Visakhapatnam-Jeypore road distance of 237 km.

It would be convenient if the Venlo-Duisburg arc were the only one needing a
published distance, but it is not: the two Eastern Ghats arcs together are 34 % of
the Visakhapatnam corridor's length, have comparable circuity, and the fitted rule
understates them by about 20 %. With the three corrections above,
**roughly 70 % of the Visakhapatnam corridor length and 60 % of the Rotterdam
corridor length is derived rather than published, and effectively all of the San
Antonio and Manzanillo corridor length is.** The circuity factor is varied from
1.00 to 1.40 in the sensitivity analysis -- but note that this sweep rescales all
arcs together and therefore cannot probe the composition error just described; a
deployment version of this model should take arc lengths from a routing engine
rather than from a fitted scalar.

Highway labels name the route actually taken, which is not always the single road a
corridor is known by: the San Antonio to Valparaiso leg is Ruta F-90 then Ruta 68,
Guadalajara to Aguascalientes is MEX-80D then MEX-45, and Utrecht to Nijmegen is
A12/A50. These labels appear in the study-area figure, where a reader will read them
as route evidence.

## 6. Corridor traffic volume

| Port | Container throughput | Road share | TEU per truck | Source |
|---|---|---|---|---|
| Visakhapatnam | 618,093 TEU (FY 2024-25) | 0.62 | 1.55 | Visakhapatnam Port Authority, *Administration Report 2024-25*: 618,093 TEU, 82.62 Mt total cargo, 31+1 berths, a 10 MW on-site solar plant |
| San Antonio | 2,060,244 TEU (2025) | 0.88 | 1.60 | Puerto San Antonio: first Chilean port above 2 M TEU, +14 % year on year (reported via Seatrade Maritime and Agenda Logistica; the port authority is the primary source) |
| Manzanillo | 3,893,357 TEU (2025) | 0.83 | 1.62 | Administracion Portuaria Integral de Manzanillo, published monthly statistics (also reported via Mexico Business News; the port authority is the primary source) |
| Rotterdam | 14.2 M TEU (2025) | 0.48 | 1.68 | Port of Rotterdam 2025 throughput: 14.2 M TEU (+3.1 %), 428.4 Mt total cargo (-1.7 %) |

Throughput figures are published measurements. The road share is applied to
**hinterland** throughput, that is to throughput net of transshipment, because
transshipped boxes never touch a road; the transshipment share is 0.30 for
Rotterdam, 0.08 for Manzanillo, 0.05 for San Antonio and 0.03 for Visakhapatnam.
The **transshipment share**, the **road share** and the
**TEU-per-truck factor** are calibrated: national modal-split statistics for
hinterland container transport are published only at coarse aggregation, and no
port publishes the road share of its own container traffic on a comparable basis.
All three enter the model only through the daily box count, so a change in any of
them is a uniform scaling of every demand -- they scale the corridor's volume
rather than changing its composition. That is a claim, not an axiom, so the
sensitivity analysis now carries a `volume_composition` block that rescales them
and reports what moves, rather than asserting the claim untested.

Two of these values deserve a caveat beyond "calibrated". Rotterdam's road share
of 0.48 is at the low end of published hinterland modal splits (road roughly
50-55 %, barge 33-35 %, rail 11-13 %) and its transshipment share of 0.30 at the
low end of the 30-45 % commonly quoted, so both choices push its hinterland road
volume *up*. And the corridor networks differ in how much of their port's real
hinterland they represent: Visakhapatnam's eight demand nodes plausibly cover most
of its hinterland, whereas Rotterdam's seven nodes receive all of Rotterdam's
hinterland road volume although its actual road hinterland reaches across Germany,
Belgium, France and Switzerland, and Manzanillo's six nodes likewise absorb all of
Manzanillo's. Arc volumes on those two corridors are therefore inflated relative to
reality, and not symmetrically across the four cases. This is a limitation of the
cross-corridor comparison and is stated as one in the paper: the four corridors are
comparable as *modelling objects* of similar structure, not as equally complete
representations of their hinterlands.

## 6a. Structural constants of the instance generator

These are modelling choices rather than measurements. They are named constants at
the top of `src/instance.py` rather than literals in the middle of it, recorded in
every instance's metadata, and listed here, so that the claim at the top of this
file -- that nothing in the model is a number without a row here -- holds of them
too.

| Constant | Value | What it is | Swept? |
|---|---|---|---|
| `OPERATING_DAYS` | 250 | working days per year the corridor is modelled over | no; a pure scaling of annual totals |
| `HEADROOM_FRACTION` | 0.75 | charging headroom in the clean state, as a fraction of the energy full electrification at mean demand would need | yes, 0.5x-2.0x |
| grid headroom multipliers | 1.00 / 0.80 / 0.45 | how headroom falls across clean, average and marginal states | only as a block, via the above |
| `ARC_CAP_MULTIPLE` | 4.0 | arc truck-movement capacity as a multiple of peak daily boxes | no; slack at every optimum observed |
| `OUTER_MASS` | 0.50 | probability mass on the two outer grid states together | no; the *mean* is pinned to the published average regardless |
| grid price spread | 0.80 / 1.00 / 1.55 | relative electricity price across the three states, rescaled so the expected price is the published national price | yes, as a level multiplier |
| `DEMAND_PROBS` | 0.30 / 0.40 / 0.30 | probabilities of the low, mid and high demand levels | no |
| `DEMAND_LEVELS` | 0.80 / 1.00 / 1.30 | demand multipliers of those levels | no |
| `SHARE_DIRICHLET` | 6.0 | concentration of the carrier size split | yes, via ten seeds |
| `TILT_DIRICHLET` | 8.0 | concentration of the node tilt at zero heterogeneity | yes, via the heterogeneity sweep |
| `PROCUREMENT_STEPS` | 127 | charging procurement steps spanned per corridor, which fixes the hub size | no; it is what makes the design space the same size on all four corridors |
| T&D loss factors | 0.17 / 0.05 / 0.12 / 0.04 | India / Chile / Mexico / Netherlands, used **only** in the alternative-accounting-boundary row of the sensitivity table | that row *is* the sweep |

Two honest notes on this table. The grid headroom construction caps the
regime matrix's headline metric by assumption: headroom is 75 % of
full-electrification energy in the clean state and 33.75 % of it in the marginal
state, so the electric share of truck movements cannot exceed 33.75 % in any
marginal state whatever the carbon price. Part of the spread that the matrix
attributes to the energy regime is therefore this ladder rather than carbon or
price, and the headroom sweep rescales all states together and so cannot separate
the two. And India's 0.17 is an aggregate technical-and-commercial loss figure
being used as a physical delivery loss, which overstates the physical loss.

## 7. Demand allocation across nodes and carriers

No public source reports container volumes by hinterland node and by carrier.
Two explicit rules stand in:

* **Across nodes.** A node's share of the corridor's road volume is its
  `demand_weight` in `data/networks/*_nodes.csv`, set in proportion to the
  district or metropolitan economic weight of the node and, where a node is
  served predominantly by barge or rail rather than road, reduced accordingly
  (Duisburg on the Rotterdam corridor is the clearest case). These weights are
  the least defensible input in the file: no source reports container volumes by
  hinterland node. Its split between import
  and export loads is `exp_share`, which encodes the directional imbalance that
  drives empty-container repositioning.
* **Across carriers.** Market shares are drawn once from a Dirichlet
  distribution with a fixed seed (20260909), and each node's volume is split
  among the carriers by a second Dirichlet draw whose concentration is the
  `heterogeneity` parameter. Setting `heterogeneity = 0` makes the carriers
  identical and the cooperative game degenerate; the paper reports the
  collaboration gain across the whole range so that the reader can see how much
  of it depends on this assumption.

These are the only stochastic elements of the instance and they are seeded, so
every number in the paper is reproducible bit for bit by
`python3 -m src.run_all`.

## 8. Cost parameters that are calibrated rather than published

| Parameter | Value | Range tested | Basis |
|---|---|---|---|
| Road-haulage cost excluding fuel | 0.32 (India), 0.55 (Chile), 0.48 (Mexico), 1.05 (Netherlands) USD/truck-km | 0.20-1.20 | National road-freight cost benchmarks: driver, vehicle capital, maintenance, insurance, tolls, overhead |
| Platoon coordination cost | 2.00 USD per truck per arc | 0.50-8.00 | Matching delay, gap-keeping telematics, dispatch overhead |
| Charging bay | 2,000 kWh/day, 26,000 USD/yr | 18,000-40,000 | One 350 kW bay at about 6 h/day and 95 % availability, annualised over 10 years at 8 % |
| Procurement unit (hub) | 1 bay at Visakhapatnam, 5 at San Antonio, 13 at Rotterdam, 38 at Manzanillo | -- | Capacity is bought in whole units, and the unit is a hub rather than a single bay. A corridor moving a thousand containers a day procures bays; a gateway moving ten thousand does not. The hub is sized so that the same number of procurement steps spans each corridor's grid headroom, which keeps the model's size -- and therefore what the cross-corridor comparison measures -- independent of corridor volume. The hub size is recorded in each instance's metadata. |
| Corridor electrification | 120,000 USD/yr fixed + 900 USD/yr per km | 80,000-200,000 and 600-1,400 | Site, HV connection and substation works annualised over 15 years at 8 %, plus medium-voltage reinforcement |
| Grid-stress externality | 0.020 USD/kWh | 0.000-0.060 | Deferred network-reinforcement value of avoided peak charging load |
| Unmet-demand penalty | 900 USD per container | 400-2,000 | Demurrage, detention and lost margin on a failed delivery |

These are the numbers a reader should push back on hardest, which is why each is
carried with an explicit range and each appears in the sensitivity table.

## 9. What this instance is not

It is a **calibrated** instance, not operator telemetry. Structural magnitudes
come from the published sources above; node-level and carrier-level splits come
from the documented rules in Section 7. It is suitable for the comparative and
threshold results the paper draws, and it is not a forecast of any particular
firm's costs. Before an authority used this model to size a real programme, the
loaders in `src/data_io.py` should be pointed at that authority's own
authenticated series, which is exactly why every input is read from a file
rather than written into the model.
