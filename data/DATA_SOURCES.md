# Data provenance for SB-PHEP-II

Every number the model consumes is listed here with the publication it comes
from and the date it was retrieved. The list is deliberately explicit about
which quantities are **published measurements**, which are **published
aggregates we transform**, and which are **transparent allocation rules** that
stand in for information no public source reports at the resolution the model
needs. Nothing in the model is a number without a row in this file.

The study covers **eight port-hinterland corridors in eight countries**:
JNPT/Nhava Sheva (India, the **focal case**), Manzanillo (Mexico), Rotterdam
(Netherlands), Los Angeles (USA), Shanghai (China), Jebel Ali (UAE), Busan (South
Korea) and Durban (South Africa). The list is fixed in `src/corridors.py`
(`NETWORKS`, `COUNTRIES`, `FOCAL = "jnpt"`).

All monetary values are in **United States dollars**. Local-currency figures and
the exchange rate used to convert them are given in `energy_regimes.csv` so that
the conversion can be redone.

Retrieval dates: **9 September 2026** for the sources carried over from the
four-corridor version (India's grid factors, prices and haulage cost; Mexico and
the Netherlands throughout; Manzanillo and Rotterdam traffic; all of Sections 3, 4
and 7); **6 October 2026** for everything added with the eight-corridor version
(JNPT traffic, and all data for the USA, China, UAE, South Korea and South Africa).
The per-row date is the `accessed` column of each CSV. Section 10 lists the primary
sources for the new data.

---

## 1. Grid carbon intensity

| Country | Clean state | Average | Marginal state | Basis |
|---|---|---|---|---|
| India | 0.512 | 0.710 | 0.961 | CEA v21.0, FY 2024-25, generation busbar, operational CO2 (all three published) |
| Mexico | 0.060 | 0.474 | 0.490 | Ember 2025 data year (lifecycle CO2e); outer states IPCC AR5 lifecycle (gas CCGT) |
| Netherlands | 0.030 | 0.254 | 0.490 | Ember 2025 data year (lifecycle CO2e); outer states IPCC AR5 lifecycle (gas CCGT) |
| USA | 0.048 | 0.384 | 0.490 | Ember *Global Electricity Review 2026*, 2025 (lifecycle CO2e); outer states IPCC AR5 lifecycle (utility PV / gas CCGT) |
| China | 0.048 | 0.525 | 0.820 | Ember *Global Electricity Review 2026*, 2025 (lifecycle CO2e); outer states IPCC AR5 lifecycle (utility PV / coal) |
| UAE | 0.048 | 0.468 | 0.490 | Ember yearly data, **2024** data year (lifecycle CO2e); outer states IPCC AR5 lifecycle (utility PV / gas CCGT) |
| South Korea | 0.048 | 0.417 | 0.490 | Ember yearly data, 2025 data year (lifecycle CO2e); outer states IPCC AR5 lifecycle (utility PV / gas CCGT) |
| South Africa | 0.048 | 0.699 | 0.820 | Ember yearly data, 2025 data year (lifecycle CO2e); outer states IPCC AR5 lifecycle (utility PV / coal) |

Units are kg CO2(e) per kWh generated; transmission and distribution losses are
*not* added. **The accounting boundary is not the same for every row, and this
should be read before any cross-country comparison.** India's CEA factors are
**operational CO2 at the generation busbar**. Ember's national averages, used for
the other seven countries, are **lifecycle CO2-equivalent** figures: Ember applies
IPCC lifecycle emission factors by generation technology, so its averages include
upstream fuel supply and plant construction. The seven non-Indian countries' grid
side is therefore on a **lifecycle boundary** throughout -- average and outer
states alike -- while India's is on a busbar operational boundary. Against either,
the base-case diesel factor is tank-to-wheel.

Because no single boundary is available for all eight countries, the paper reports
the threshold position of every grid factor on **both** boundaries: the
busbar/tank-to-wheel boundary of the base case, and a delivered/well-to-wheel
boundary in which the grid factor is grossed up by each country's T&D losses
(Section 6a) and diesel is taken well-to-wheel (3.20 kg CO2/L). **The paper relies
only on conclusions that agree on both boundaries**; a verdict that changes sign
between them is reported as boundary-dependent rather than as a finding.

**India is the only country for which all three states are published**, and this
matters for the paper's central result, because India is the focal case. CEA v21.0
reports, for FY 2024-25, a weighted-average grid emission factor of **0.710
tCO2/MWh**, a CDM **simple operating margin of 0.961** and a **build margin of
0.512**; it also reports the CDM **combined margin of 0.736** (the equal-weight
blend of the two margins), which `energy_regimes.csv` carries as `ef_grid_combined`
and which appears in the threshold table but is not a state of the scenario tree.
We map the build margin to the "clean" state, the weighted average to the
"average" state and the operating margin to the "marginal" state. **That mapping
is our interpretation, not the CEA's.** The CDM operating margin is the
generation-weighted average of all non-must-run plant, not a short-run marginal
factor for a particular hour, and the build margin is the intensity of recent
capacity additions, not a renewable-rich hour. What makes the mapping defensible
is direction rather than identity: incremental load is served by dispatchable
plant, whose intensity the operating margin measures, and new capacity is what
eventually serves it. What makes it worth stating clearly is that the paper's
headline turns on the distance between two of these numbers.

Ember's figure for India is **0.670**, about 6% below the CEA weighted average
we use; it is a lifecycle figure, and it has not been independently re-verified
for this version. India's "average" therefore sits on a different basis
(operational, busbar) from the other seven rows, which are Ember lifecycle figures
throughout. We use
CEA for India because it is the only source that publishes the margins.

For the **seven other countries** no equivalent national margin series is
published, so the average is Ember's national figure and the two outer states are
constructed:

* **Average.** Ember's national figure, a lifecycle CO2-equivalent value. For Mexico, the Netherlands,
  South Korea and South Africa it is the 2025 data year of Ember's yearly
  electricity data; for the USA (384 gCO2/kWh) and China (525 gCO2/kWh) it is the
  2025 figure reported in Ember's *Global Electricity Review 2026*. **The UAE's
  0.468 is the 2024 data year**, the latest located, and is therefore one vintage
  older than the other rows. The South Korea, South Africa and UAE values were
  compiled from Ember's data by GreenCalculus; Ember is the primary source.
* **Marginal state.** The IPCC AR5 **lifecycle** median of the technology that
  typically sets the margin: combined-cycle gas at **0.490** for the USA, the UAE,
  South Korea, Mexico and the Netherlands, and coal at **0.820** for China and
  South Africa.
* **Clean state.** For the five countries added in the eight-corridor version
  (USA, China, UAE, South Korea, South Africa) it is the IPCC AR5 lifecycle median
  for utility-scale solar PV, **0.048**, standing for a solar-rich hour. Mexico
  (0.060) and the Netherlands (0.030) keep the renewable-rich-hour values of the
  earlier version.

**These outer states are constructed, not published, and they are the least
authoritative numbers in the study.** They are on the same lifecycle boundary as
Ember's averages, so within each non-Indian row the three states are consistent
in boundary; it is between India and the other seven that the boundary differs.

Two further candours about the outer states. First, for two countries the
published average and the constructed marginal state are almost the same number:
Mexico's 0.474 is 3 % below its 0.490 marginal state and the UAE's 0.468 is 5 %
below its own, so on published data neither has much marginal signal. Because the
tree is pinned to the published average (below), the solved probability of their
clean state is correspondingly tiny -- about 0.02 for Mexico and 0.03 for the UAE
at `OUTER_MASS = 0.50` -- and almost all the outer mass falls on the marginal
state. The wide clean-to-marginal spread of these two rows is therefore a property
of the construction that the calibration largely switches off, not a property of
either system. Second, the clean states are below anything most of these systems
reach in practice: Mexico, the USA, China, the UAE, South Korea and South Africa
are all majority-fossil, with annual means between 0.384 and 0.699. The clean
states should be read as the cleanest hour a corridor operator could *choose* to
charge in under a future mix, not as an observed hour today.

### How the states are weighted, and why

The weighting is easy to get wrong, so it is worth setting out. Take two states
(clean and marginal) with fixed equal probabilities: the expected grid factor of
such a tree reproduces no published number -- on this data Mexico and the UAE
would come out about 42 % cleaner than their published annual averages, South
Africa 38 % cleaner, and India 4 % dirtier. Every cross-country statement would
then be a statement about the construction rather than about the country, and the
one published, measured grid number per country -- the annual average -- would
play no part in any computation.

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

| Country | Business electricity (USD/kWh) | Electricity source | Diesel (USD/L) | Diesel, local | Diesel snapshot |
|---|---|---|---|---|---|
| India | 0.122 | GlobalPetrolPrices comparison table (multi-year average) | 1.060 | INR 90.58-103.82 /L | GlobalPetrolPrices 9 Mar 2026; Indian metro retail (Goodreturns/PPAC) 9 Sep 2026 |
| Mexico | 0.213 | GlobalPetrolPrices comparison table (multi-year average) | 1.470 | MXN 26.23 /L | GlobalPetrolPrices 12 Jan 2026 |
| Netherlands | 0.220 | GlobalPetrolPrices comparison table (multi-year average) | 2.170 | EUR 1.82 /L | GlobalPetrolPrices 9 Feb 2026 |
| USA | 0.134 | US EIA *Short-Term Energy Outlook*, Table 7c: 2025 average commercial-sector price, 13.41 US cents/kWh | 0.970 | USD 0.97 /L | GlobalPetrolPrices 9 Feb 2026 (consistent with the EIA 2025 annual average of USD 3.66/gal) |
| China | 0.115 | GlobalPetrolPrices business price, June 2025: CNY 0.796/kWh | 0.930 | CNY 6.41 /L | GlobalPetrolPrices 9 Feb 2026 |
| UAE | 0.110 | GlobalPetrolPrices business price, June 2025: AED 0.405/kWh | 0.780 | AED 2.85 /L | GlobalPetrolPrices 8 Dec 2025 |
| South Korea | 0.118 | GlobalPetrolPrices business price, June 2025: KRW 154.85/kWh | 1.260 | KRW 1,662.89 /L | GlobalPetrolPrices 8 Dec 2025 |
| South Africa | 0.143 | GlobalPetrolPrices business price, June 2025: ZAR 2.289/kWh | 1.300 | ZAR 20.72 /L | GlobalPetrolPrices 9 Feb 2026 |

**Currency convention.** Local prices are converted at the USD value that
GlobalPetrolPrices reports alongside them at the time of retrieval (the EIA price
for the USA is already in USD). The `fx_per_usd` column of `energy_regimes.csv`
records the implied rate, which is therefore not a single-date or annual-average
market rate: South Korea's KRW 1,312 per USD, for example, compares with a market
average of about KRW 1,421 in 2025. Exchange-rate differences of this order are
within the electricity- and diesel-price multipliers swept in the sensitivity
analysis.

**The electricity prices are not all on one basis, and this should be said
plainly.** For India, Mexico and the Netherlands they are GlobalPetrolPrices'
business/industrial series from its international comparison table, which the
source recommends over a single-quarter snapshot because it removes
quarter-to-quarter volatility. For China, the UAE, South Korea and South Africa
they are GlobalPetrolPrices' **June 2025 single-quarter** business price (the
China note records that it includes network costs and taxes). For the USA the price is the US EIA's 2025 annual average
commercial-sector retail price from the *Short-Term Energy Outlook*, Table 7c. All three are business tariffs at the meter rather
than wholesale prices, so they are comparable in kind, but a reader comparing two
countries' prices to the cent should know that they are not one series. The source's
own India country page quotes 0.116 USD/kWh for June 2025, about 5% below the
comparison-table value used here; the difference is well inside the sensitivity
range. The diesel snapshots are on different dates (8 December 2025 to 9 March
2026) because the source updates countries on different cycles; the dates are
recorded per country in `energy_regimes.csv` and the spread between them is well
inside the sensitivity range reported in the paper.

For India the retail diesel price on 9 September 2026 ranged from INR 97.83
(Mumbai) to INR 103.82 (Hyderabad); we use USD 1.06/L, corresponding to about INR
98/L at the stated exchange rate, which is the Mumbai price -- the metro served by
the focal JNPT corridor.

Within a scenario, the electricity price is the national business price
multiplied by a state factor (0.80 clean, 1.00 average, 1.55 marginal) that
represents the intraday spread between renewable-rich and scarcity-priced hours,
rescaled as described in Section 1 so that the expected price equals the published
national price. The multipliers are **calibrated, not published**, and are varied
in the sensitivity analysis.

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
by a per-corridor circuity factor (`circuity` in `data/ports.csv`). Where a
published driving distance is known, it goes in the `road_km` column of the arcs
file and overrides the derived value.

**The circuity factor is fitted, not validated.** It is chosen, one per corridor,
so that the derived length of a single reference route matches the published
driving distance for that route (the `circuity_check` column of `ports.csv`).
Reporting that it then reproduces that distance would be circular, so what the
table below reports is the reference route and its residual, and the text after
it the fact that individual arcs can be much further out.

| Corridor | Circuity | Reference route (`circuity_check`) | Great circle / derived | Published | Residual of fitted rule |
|---|---|---|---|---|---|
| JNPT | 1.20 | Mumbai-Pune Expressway, Kalamboli to Kiwale | 79.0 km great circle | 94.5 km (ratio 1.196) | +0.3 % |
| Manzanillo | 1.35 | Port to Guadalajara, MEX-54D | 311.5 km derived | ~310 km | +0.5 % |
| Rotterdam | 1.12 | Maasvlakte to Venlo, A15/A16/A58/A67 | 187.0 km derived | ~180 km | +3.9 % |
| Los Angeles | 1.18 | Los Angeles to Las Vegas, I-15 | 367.6 km great circle | ~435 km (ratio 1.18) | -0.3 % |
| Shanghai | 1.10 | G42 Huning Expressway, termini Zhenru (Shanghai) to Maqun (Nanjing) | ~250 km great circle | 274 km (ratio 1.10) | +0.4 % |
| Jebel Ali | 1.14 | Dubai to Abu Dhabi, E11 | 122.9 km great circle | ~140 km (ratio 1.14) | +0.1 % |
| Busan | 1.30 | Gyeongbu Expressway, Seoul to Busan termini | ~310-315 km great circle | 416 km (ratio 1.32-1.34) | -1.5 to -3.1 % |
| Durban | 1.14 | Durban to Johannesburg, N3 | 500.3 km great circle | ~568-578 km (ratio 1.14-1.16) | +0.4 to -1.3 % |

Notes on the reference routes of the corridors added in the eight-corridor
version:

* **JNPT.** The reference pair is the expressway section from Kalamboli (the
  corridor's junction node) towards Pune, not a port-to-town route; the
  port-access leg itself is derived.
* **Los Angeles.** The reference is the long desert I-15 run to Las Vegas, which
  is also the corridor's longest chain (port - Commerce - Industry - Ontario - San
  Bernardino - Barstow - Las Vegas). The dense Inland Empire legs are short and
  may carry a different circuity in practice.
* **Shanghai.** The G42's published length of 274 km is measured between its
  termini at Zhenru (Shanghai) and Maqun (Nanjing), about 250 km apart on a great
  circle, so 1.10 is the fitted value. The port node is placed at Waigaoqiao, although about half of Shanghai's volume
  is handled at Yangshan, which is further from the hinterland.
* **Jebel Ali.** Dubai-Abu Dhabi on the E11 is the corridor's busiest axis; the
  inland legs to Al Ain and the mountain crossing to Fujairah (E88) are derived
  at the same coastal-motorway factor and are likely understated.
* **Busan.** The Gyeongbu reference runs the full length of the corridor to the
  Seoul capital region: 416 km against about 310-315 km between its termini on a
  great circle, a ratio of 1.32-1.34. The corridor uses **1.30**, slightly below
  the fitted range, so derived lengths on this corridor may be up to about 3 %
  short. The same factor is applied to all arcs, including short coastal legs
  where the true circuity may differ.
* **Durban.** The N3 to Johannesburg is the corridor's spine; published driving
  distances range from about 568 to 578 km depending on the end points, a circuity
  of 1.14-1.16, and the lower value is used. The N11, N5 and N12 branches are
  derived at the same factor.

Individual arcs are worse than the reference routes, and the failures are
**patterned, not random**: a single fitted factor understates port-access and
mountain legs and overstates flat motorway legs. One arc in the package is far
enough out to carry its own `road_km` value rather than the fitted rule:

| Arc | Great circle | Fitted rule | Published road | Implied circuity |
|---|---|---|---|---|
| Venlo to Duisburg (A67/A40) | 41.5 km | 46.5 km | **75 km** | 1.8 |

No other arc in the eight networks has a published road distance. Of the
corridors' total modelled length, **only 75 of Rotterdam's 447 km (17 %) is
published; the rest of Rotterdam and effectively all of the other seven corridors'
length is derived** from coordinates and a fitted scalar. The total derived
lengths are 1,156 km (JNPT, 11 arcs), 1,380 km (Manzanillo, 8), 447 km
(Rotterdam, 9), 1,318 km (Los Angeles, 9), 673 km (Shanghai, 10), 628 km (Jebel
Ali, 9), 682 km (Busan, 10) and 1,243 km (Durban, 9). The circuity factor is varied
from 1.00 to 1.40 in the sensitivity analysis -- but note that this sweep rescales
all arcs together and therefore cannot probe the composition error just
described; a deployment version of this model should take arc lengths from a
routing engine rather than from a fitted scalar.

**Nodes** (from `data/networks/<name>_nodes.csv`; demand weights in brackets):

| Corridor | Port node | Junction | Demand nodes |
|---|---|---|---|
| JNPT (`jnpt`) | Nhava Sheva | Kalamboli | Bhiwandi (0.20), Chakan-Talegaon (0.16), Pune (0.14), Nashik (0.11), Aurangabad (0.09), Ahmednagar (0.06), Vapi (0.10), Surat (0.14) |
| Manzanillo (`manzanillo`) | Manzanillo Port | Colima | Ciudad Guzman (0.06), Guadalajara (0.28), Aguascalientes (0.10), Leon-Bajio (0.16), Queretaro (0.15), Mexico City (0.25) |
| Rotterdam (`rotterdam`) | Rotterdam Maasvlakte | Rotterdam Waalhaven | Moerdijk (0.11), Tilburg (0.18), Eindhoven (0.17), Venlo (0.16), Duisburg (0.09), Nijmegen (0.11), Utrecht (0.18) |
| Los Angeles (`losangeles`) | Port of Los Angeles | Commerce (I-710/I-5) | City of Industry (0.16), Ontario (0.22), Moreno Valley (0.14), San Bernardino (0.13), Barstow (0.05), Las Vegas (0.09), Bakersfield (0.08), Phoenix (0.13) |
| Shanghai (`shanghai`) | Shanghai Waigaoqiao | Shanghai Jiading | Kunshan (0.13), Suzhou (0.20), Wuxi (0.13), Changzhou (0.09), Nanjing (0.11), Jiaxing (0.09), Hangzhou (0.17), Huzhou (0.08) |
| Jebel Ali (`jebelali`) | Jebel Ali Port | none | Dubai Al Quoz (0.24), Sharjah Industrial (0.18), Ajman (0.07), Ras Al Khaimah (0.07), Abu Dhabi Mussafah (0.18), Al Ain (0.08), Fujairah (0.06), Dubai Industrial City (0.12) |
| Busan (`busan`) | Gadeok (Busan New Port) | Gimhae JC | Changwon (0.14), Yangsan ICD (0.12), Ulsan (0.12), Daegu (0.13), Gumi (0.10), Daejeon (0.08), Uiwang ICD (Seoul) (0.24), Pohang (0.07) |
| Durban (`durban`) | Durban Container Terminal | Pinetown | Pietermaritzburg (0.10), Ladysmith (0.05), Harrismith (0.04), Johannesburg City Deep (0.36), Pretoria (0.18), Newcastle (0.06), Bloemfontein (0.08), eMalahleni (0.13) |

Highway labels name the route actually taken, which is not always the single road
a corridor is known by: Guadalajara to Aguascalientes is MEX-80D then MEX-45,
Utrecht to Nijmegen is A12/A50, the Shanghai-Nanjing chain is G2/G42, Yangsan to
Daegu is Gyeongbu/Jungang, Sharjah is reached by E11/E311 and Dubai Industrial
City by E611/E77, and the JNPT port-access leg is SH-54/JNPT road. These labels
appear in the study-area figure, where a reader will read them as route evidence.

## 6. Corridor traffic volume

| Port | Container throughput | Transshipment share | Road share | TEU per truck | Road boxes/day | Source |
|---|---|---|---|---|---|---|
| JNPT | 7.3 M TEU (FY 2024-25) | 0.03 (cal.) | 0.85 (from published rail volume) | 1.55 (cal.) | 15,533 | Jawaharlal Nehru Port Authority via Maritime Gateway (2025): record 7.3 M TEU (+13.55 %), of which 1,078,315 TEU moved by rail |
| Manzanillo | 3,893,357 TEU (2025) | 0.08 (cal.) | 0.83 (cal.) | 1.62 (cal.) | 7,341 | Administracion del Sistema Portuario Nacional Manzanillo, published statistics (via Mexico Business News) |
| Rotterdam | 14.2 M TEU (2025) | 0.30 (cal.) | 0.48 (cal.) | 1.68 (cal.) | 11,360 | Port of Rotterdam 2025 throughput: 14.2 M TEU (+3.1 %), 428.4 Mt total cargo (-1.7 %) |
| Los Angeles | 10,239,318 TEU (2025) | 0.00 (negligible) | 0.70 (cal.) | 1.75 (cal.) | 16,383 | Port of Los Angeles, *Container Statistics 2025* (loaded imports 5,316,713; loaded exports 1,429,260; empties 3,493,344) |
| Shanghai | 55.06 M TEU (2025) | 0.144 (published) | 0.45 (cal.) | 1.60 (cal.) | 53,023 | Port of Shanghai via Container News (2026): 55.06 M TEU (+6.9 %), international transshipment 7.911 M TEU (14.4 %), sea-rail 1 M TEU |
| Jebel Ali | 15.6 M TEU (2025) | 0.50 (cal.) | 0.95 (cal.) | 1.60 (cal.) | 18,525 | DP World FY2025 results: 15.6 M TEU (+0.1 %) |
| Busan | 24.8 M TEU (2025) | 0.57 (published) | 0.92 (cal.) | 1.60 (cal.) | 24,527 | Busan Port Authority via Kuehne+Nagel (2026): 24.8 M TEU (+2 %), transshipment 14.1 M TEU (57 %) |
| Durban | 2,659,617 TEU (FY 2024-25, **derived; share calibrated**) | 0.10 (cal.) | 0.85 (cal.) | 1.60 (cal.) | 5,087 | Transnet Port Terminals: 4,091,718 TEU nationally in FY 2024/25; the Port of Durban handles over 60 % of South Africa's container volume (Transnet; BusinessDay, 13 May 2026); calibrated share 0.65 x 4,091,718 = 2,659,617 TEU |

"cal." = calibrated. Road boxes per day are computed by `src/instance.py` as
TEU x (1 - transshipment) x road share / TEU per truck / 250 operating days, and
are recorded as `daily_boxes` in each instance's metadata.

Throughput figures are published measurements, with one exception: **Durban's is
derived, and the share used to derive it is calibrated.** Transnet Port Terminals
publishes national throughput (4,091,718 TEU in FY 2024/25), and Transnet states
that the Port of Durban handles "over 60 %" of South Africa's container volume
(reported by BusinessDay, 13 May 2026). The 65 % figure that Transnet also
publishes is the Durban Container Terminal's share of the **port's own**
throughput, not of the national total, so it cannot be applied to the national
figure as a published share. The 0.65 used here is therefore a calibrated value
consistent with "over 60 %", not a published one. The road share is
applied to **hinterland** throughput, that is to throughput net of transshipment,
because transshipped boxes never touch a road.

What is published and what is calibrated among the three shares:

* **Transshipment share.** Published for **Shanghai** (14.4 %) and **Busan**
  (57 %). Calibrated for JNPT (0.03, a gateway port with little transshipment),
  Manzanillo (0.08), Rotterdam (0.30), Jebel Ali (0.50, a major Gulf hub whose
  share is not published) and Durban (0.10); taken as negligible for Los Angeles.
* **Road share.** For **JNPT** it is derived from a published figure: rail carried
  1,078,315 TEU, 14.8 % of throughput, so road carries about 85 % of hinterland
  boxes (the rail share is taken of total rather than hinterland throughput; at a
  3 % transshipment share the difference is under one percentage point). Every
  other road share is calibrated: no other port in the set publishes the road share
  of its own container traffic on a comparable basis, and national modal-split
  statistics for hinterland container transport are published only at coarse
  aggregation.
* **TEU-per-truck factor.** Calibrated everywhere; Los Angeles is set highest
  (1.75) to reflect the predominance of 40-ft boxes.

All three enter the model only through the daily box count, so a change in any of
them is a uniform scaling of every demand -- they scale the corridor's volume
rather than changing its composition. That is a claim, not an axiom, so the
sensitivity analysis carries a `volume_composition` block that rescales them and
reports what moves, rather than asserting the claim untested.

Several values deserve a caveat beyond "calibrated". Rotterdam's road share of
0.48 is at the low end of published hinterland modal splits (road roughly 50-55 %,
barge 33-35 %, rail 11-13 %) and its transshipment share of 0.30 at the low end of
the 30-45 % commonly quoted, so both choices push its hinterland road volume *up*.
Shanghai's road share of 0.45 reflects the large share of hinterland boxes that
moves by Yangtze and canal barge, and is the most consequential calibrated share
in the set because it multiplies the largest throughput.

The corridor networks also differ in how much of their port's real hinterland
they represent. Each network assigns **all** of its port's hinterland road volume
to its six to eight demand nodes. Where those nodes plausibly cover most of the road
hinterland -- JNPT's Maharashtra-Gujarat nodes, Durban's N3 chain to Gauteng,
the emirates around Jebel Ali -- the distortion is smaller. Where the
real road hinterland is much wider than the network -- Rotterdam's reaches across
Germany, Belgium, France and Switzerland, and Shanghai's eight Yangtze-delta nodes
absorb about 53,000 boxes a day -- arc volumes are inflated relative to reality,
and not symmetrically across the eight cases. This is a limitation of the
cross-corridor comparison and is stated as one in the paper: the eight corridors
are comparable as *modelling objects* of similar structure, not as equally
complete representations of their hinterlands.

## 6a. Structural constants of the instance generator

These are modelling choices rather than measurements. They are named constants at
the top of `src/instance.py` (and, for the T&D losses, `src/experiments.py`)
rather than literals in the middle of the code, recorded in every instance's
metadata, and listed here, so that the claim at the top of this file -- that
nothing in the model is a number without a row here -- holds of them too.

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
| `PROCUREMENT_STEPS` | 127 | charging procurement steps spanned per corridor, which fixes the hub size | no; it is what makes the design space the same size on all eight corridors |
| T&D loss factors (`TD_LOSSES`, `src/experiments.py`) | India 0.17, Mexico 0.12, Netherlands 0.04; **0.10 default** for the USA, China, UAE, South Korea and South Africa | used **only** in the alternative-accounting-boundary row of the sensitivity table and the threshold table | that row *is* the sweep |

Two honest notes on this table. The grid headroom construction caps the
regime matrix's headline metric by assumption: headroom is 75 % of
full-electrification energy in the clean state and 33.75 % of it in the marginal
state, so the electric share of truck movements cannot exceed 33.75 % in any
marginal state whatever the carbon price. Part of the spread that the matrix
attributes to the energy regime is therefore this ladder rather than carbon or
price, and the headroom sweep rescales all states together and so cannot separate
the two. And the T&D loss factors are uneven in quality: India's 0.17 is an
aggregate technical-and-commercial loss figure being used as a physical delivery
loss, which overstates the physical loss, and the five countries added in the
eight-corridor version have **no country-specific value** in the code -- they fall
back on a uniform 0.10 placeholder, which is not a published figure for any of
them.

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
| Road-haulage cost excluding fuel | 0.32 (India), 0.48 (Mexico), 1.05 (Netherlands), 1.11 (USA), 0.40 (China), 0.50 (UAE), 0.85 (South Korea), 0.45 (South Africa) USD/truck-km | 0.20-1.20 | See below: one published benchmark (USA), three carried-over calibrations, four calibrated assumptions |
| Platoon coordination cost | 2.00 USD per truck per arc | 0.50-8.00 | Matching delay, gap-keeping telematics, dispatch overhead |
| Charging bay | 2,000 kWh/day, 26,000 USD/yr | 18,000-40,000 | One 350 kW bay at about 6 h/day and 95 % availability, annualised over 10 years at 8 % |
| Procurement unit (hub) | JNPT 25 bays, Manzanillo 38, Rotterdam 13, Los Angeles 33, Shanghai 72, Jebel Ali 12, Busan 43, Durban 23 | -- | Capacity is bought in whole units, and the unit is a hub rather than a single bay. A corridor moving a few thousand containers a day procures in small hubs; a gateway moving fifty thousand does not procure bay by bay. The hub is sized so that the same number of procurement steps (`PROCUREMENT_STEPS` = 127) spans each corridor's grid headroom, which keeps the model's size -- and therefore what the cross-corridor comparison measures -- independent of corridor volume. The hub size is recorded as `bays_per_hub` in each instance's metadata; the values here are from `build_instance(<corridor>)` at default arguments. |
| Corridor electrification | 120,000 USD/yr fixed + 900 USD/yr per km | 80,000-200,000 and 600-1,400 | Site, HV connection and substation works annualised over 15 years at 8 %, plus a distance-proportional charging-site component |
| Grid-stress externality | 0.020 USD/kWh | 0.000-0.060 | Deferred network-reinforcement value of avoided peak charging load |
| Unmet-demand penalty | 900 USD per container | 400-2,000 | Demurrage, detention and lost margin on a failed delivery |

**The haulage cost is the least uniform row in the study, and its basis differs by
country** (column `wage_usd_km` and its `wage_source` note in `energy_regimes.csv`):

* **USA, 1.11 USD/km -- published benchmark.** ATRI, *An Analysis of the
  Operational Costs of Trucking: 2025 Update* (2024 data): non-fuel marginal cost
  of USD 1.779 per mile (driver wages and benefits, truck payments, repair,
  insurance, permits, tyres, tolls) = USD 1.11 per km.
* **India 0.32, Mexico 0.48, Netherlands 1.05 -- calibrated**, as in the
  four-corridor version, from published national road-freight cost benchmarks
  (driver, vehicle capital, maintenance, insurance, tolls and overhead).
* **China 0.40, UAE 0.50, South Korea 0.85, South Africa 0.45 -- calibrated
  assumptions.** No published per-kilometre road-haulage cost benchmark excluding
  fuel was located for these countries; the values are set relative to national
  truck-driver wage levels and are not taken from any single source.

All eight lie inside the 0.20-1.20 USD/km sensitivity range. The USA value sits
near the top of that range and the four assumed values in its lower-middle; since
the haulage cost varies more than threefold across the eight countries and is not a
property of any power system, the regime matrix also reports a grid-only swap
(`grid_country`) that holds it fixed.

These are the numbers a reader should push back on hardest, which is why each is
carried with an explicit range and each appears in the sensitivity table.

**How the sensitivity sweep is solved.** In the current version the sweep
evaluates the F4 design via Corollary S2, which makes each point exact at **zero
MIP gap**. Formulations F1-F3 on the non-focal corridors were run with **300 s time
limits**; where a time-limited run returned a worse design than F0, the F0 design
is retained. Each row of the sensitivity tables records its certified MIP gap and
solver status.

## 9. What this instance is not

It is a **calibrated** instance, not operator telemetry. Structural magnitudes
come from the published sources above; node-level and carrier-level splits come
from the documented rules in Section 7. **JNPT/Nhava Sheva is the focal case**:
it is the corridor on which the single-corridor experiments in `src/run_all.py`
(sensitivity, scalability, collaboration seeds, scenario stability) are run, and
India is the one country whose three grid states are all published. The other
seven corridors are comparators whose grid outer states, several traffic shares
and four haulage costs are constructed or calibrated, as flagged above. The
instance is suitable for the comparative and threshold results the paper draws,
and it is not a forecast of any particular firm's costs. Before an authority used
this model to size a real programme, the loaders in `src/data_io.py` should be
pointed at that authority's own authenticated series, which is exactly why every
input is read from a file rather than written into the model.

## 10. Primary sources for the eight-corridor data

Retrieved **6 October 2026** unless stated otherwise.

Traffic (`data/ports.csv`):

* Jawaharlal Nehru Port Authority, FY 2024-25 throughput (7.3 M TEU; 1,078,315 rail
  TEU), as reported by *Maritime Gateway* (2025):
  https://www.maritimegateway.com/jnpa-handles-record-7-3-million-teus-cargo-in-fy-2024-25/
* Port of Los Angeles, container throughput, calendar 2025, as reported by
  *Container News*:
  https://container-news.com/port-of-los-angeles-container-throughput-tops-10-2-million-teus-in-2025
* Port of Shanghai 2025 throughput, transshipment and sea-rail volumes, as reported
  by *Container News* (2026):
  https://container-news.com/port-of-shanghai-handles-55-06-million-teus-in-2025
* DP World, *FY2025 results* (Jebel Ali throughput), as reported by *The Maritime
  Standard*: https://www.themaritimestandard.com/?p=31957
* Busan Port Authority 2025 throughput and transshipment, as reported by
  Kuehne+Nagel (2026):
  https://mykn.kuehne-nagel.com/news/article/busan-records-all-time-high-in-cargo-handling
* Transnet Port Terminals, 2025 performance report (FY 2024/25 national
  throughput):
  https://uploads1.craft.co/uploads/unified_record/source/document/2153913/c03c5cf693dad50a.pdf
* *BusinessDay*, 13 May 2026, "Transnet ports hit 15-year high as recovery gains
  traction" (Port of Durban's share of national container volume, "over 60 %"):
  https://www.businessday.co.za/news/2026-05-13-transnet-ports-hit-15-year-high-as-recovery-gains-traction/

Road distances for the circuity reference routes (`circuity_check` in
`data/ports.csv`):

* Wikipedia, *Shanghai–Nanjing Expressway*:
  https://en.wikipedia.org/wiki/Shanghai%E2%80%93Nanjing_Expressway
* Wikipedia, *Gyeongbu Expressway*: https://en.wikipedia.org/wiki/Gyeongbu_Expressway
* Wikipedia, *N3 road (South Africa)*:
  https://en.wikipedia.org/wiki/N3_road_(South_Africa)
* Wikipedia, *Mumbai–Pune Expressway*:
  https://en.wikipedia.org/wiki/Mumbai%E2%80%93Pune_Expressway

Grid carbon intensity (`data/energy_regimes.csv`):

* Ember, *Global Electricity Review 2026*, major countries and regions (USA and
  China, 2025):
  https://ember-energy.org/latest-insights/global-electricity-review-2026/major-countries-and-regions
* Ember, methodology and supporting materials (lifecycle emission factors by
  technology):
  https://ember-energy.org/latest-insights/global-electricity-review-2024/supporting-materials
* Ember, *Yearly Electricity Data* (2025 release): South Korea and South Africa
  (2025 data year) and UAE (2024 data year), as compiled by GreenCalculus:
  https://greencalculus.com/data/grid-electricity-emission-factors/ ; Mexico and
  the Netherlands (2025 data year, retrieved 9 September 2026).
* IPCC AR5 lifecycle emission medians (utility-scale solar PV 0.048,
  combined-cycle gas 0.490, coal 0.820 kgCO2eq/kWh).

Prices and costs (`data/energy_regimes.csv`):

* US Energy Information Administration, *Short-Term Energy Outlook*, Table 7c
  (2025 average commercial-sector electricity price):
  https://www.eia.gov/outlooks/steo/tables/pdf/7ctab.pdf ; and the EIA 2025 annual
  average diesel price used as a cross-check on the USA diesel snapshot.
* GlobalPetrolPrices (https://www.globalpetrolprices.com): business electricity
  prices, June 2025 (China, UAE, South Korea, South Africa); diesel prices of 8
  December 2025 (UAE, South Korea) and 9 February 2026 (USA, China, South Africa).
* American Transportation Research Institute (ATRI), *An Analysis of the
  Operational Costs of Trucking: 2025 Update*:
  https://truckingresearch.org/2025/07/new-atri-report-shows-trucking-profitability-severly-squeezed-by-high-costs-low-rates/
