# Data provenance for SB-PHEP-II

Every number the model consumes is listed here with the publication it comes
from and the date it was retrieved. The list is deliberately explicit about which
quantities are **published measurements**, which are **published figures we
transform**, and which are **transparent allocation rules or calibrations** that
stand in for information no public source reports at the resolution the model
needs.

*Version note: this file replaces the earlier eight-corridor version (Manzanillo,
Busan, Durban, San Antonio and Visakhapatnam were corridors or candidates in
earlier versions and no longer appear anywhere in the model or in this file).*

The study covers **ten port-hinterland corridors**. The lead (deep-dive) corridor
is **Rotterdam** (`FOCAL = "rotterdam"` in `src/corridors.py`).

| Corridor (`network`) | Port | Country / grid regime (`country` key) |
|---|---|---|
| `rotterdam` (lead) | Rotterdam | Netherlands |
| `antwerp` | Antwerp-Bruges | Belgium |
| `shanghai` | Shanghai | China-East (East China grid) |
| `ningbo` | Ningbo-Zhoushan | China-East (East China grid) |
| `qingdao` | Qingdao | China-North (North China grid) |
| `tianjin` | Tianjin | China-North (North China grid) |
| `shenzhen` | Shenzhen | China-South (Southern China grid) |
| `sanpedrobay` | Los Angeles-Long Beach (San Pedro Bay) | USA-California (eGRID subregion CAMX) |
| `jebelali` | Jebel Ali | UAE |
| `jnpt` | Jawaharlal Nehru Port (Nhava Sheva) | India |

Ten corridors share **eight grid/energy regimes** (`COUNTRIES` in
`src/corridors.py`): the two East-China corridors share one regime, as do the two
North-China corridors.

All monetary values are in **United States dollars**. Local-currency figures and
the exchange rate used to convert them are in `energy_regimes.csv` so that the
conversion can be redone. Emission factors are in **kg CO2 (or CO2e) per kWh**,
numerically equal to t CO2/MWh.

**Retrieval dates.** Rows added or revised in the ten-corridor version carry
`accessed = 2026-10-07` in `ports.csv` and `energy_regimes.csv`; India's energy
regime row carries 2026-09-09 (its CEA v22.0 grid factors were retrieved on
2026-10-07, as recorded in `grid_factor_sources.csv`) and `parameters.csv` carries
2026-09-09 or 2026-09-10 per row. Section 10 gives the sources and URLs.

**Authoritative inputs.** `data/ports.csv`, `energy_regimes.csv`, `parameters.csv`,
`node_populations.csv`, `grid_factor_sources.csv`, `node_coordinate_sources.csv`,
`atlas_ports.csv` and `data/networks/<corridor>_nodes.csv` / `_arcs.csv`. Code that
reads or transforms them: `src/data_io.py`, `src/corridors.py`, `src/instance.py`
and `src/experiments.py`. Where this file and a CSV disagree, the CSV is what the
model reads.

---

## 1. Grid emission factors

### 1.1 The factors the model uses

Three factors per regime are states of the scenario tree: **cleanest** (`ef_grid_clean`),
**average** (`ef_grid_avg`) and **marginal** (`ef_grid_marginal`). A fourth, the
**combined margin** (`ef_grid_combined`), is carried for the threshold table only
and is not a scenario state.

| Regime (corridors) | Cleanest | Average | Marginal | Combined | Basis of each factor |
|---|---|---|---|---|---|
| Netherlands (Rotterdam) | 0.175 | 0.200 | 0.315 | 0.221 | Average: **operational**, CBS 2024 (direct, integral method), published. Cleanest and marginal: **operational**, derived from the published IFI v2.0 combined-margin pair (Section 1.3). Combined: IFI v2.0 firm combined margin, published |
| Belgium (Antwerp) | 0.061 | 0.150 | 0.252 | 0.124 | Average: **lifecycle** (Ember, 2025). Cleanest and marginal: operational, derived from the published IFI v3.2 combined-margin pair (via EIB). Combined: IFI v3.2 firm combined margin, published |
| China-East (Shanghai, Ningbo) | 0.195 | 0.550 | 0.778 | 0.487 | All **operational** (direct CO2); average (MEE/NBS 2023) and both margins (NCSC 2024 edition) published; combined computed (Section 1.4) |
| China-North (Qingdao, Tianjin) | 0.310 | 0.636 | 0.953 | 0.631 | as China-East |
| China-South (Shenzhen) | 0.182 | 0.404 | 0.791 | 0.486 | as China-East |
| USA-California (San Pedro Bay) | 0.000 | 0.194 | 0.435 | none | **Operational** (direct combustion), eGRID2023 CAMX; average published, marginal a published EPA proxy; cleanest = bound 0, a physical bound, not published (Section 1.5) |
| UAE (Jebel Ali) | 0.220 | 0.468 | 0.623 | 0.353 | Average: **lifecycle** (Ember, 2024 data year). Cleanest and marginal: operational, derived from the published IFI v2.0 combined-margin pair. Combined: IFI v2.0 firm combined margin, published |
| India (JNPT) | 0.446 | 0.675 | 0.963 | 0.705 | All **operational** at the generation busbar, CEA v22.0 (August 2026), FY2025-26, Table S; all published |

Units: kg CO2(e)/kWh. Transmission and distribution losses are not added in the
base case. **The accounting boundary is not uniform across regimes**:

* *Operational / direct* (diesel comparator: tank-to-wheel, 2.68 kg/L): the
  Netherlands average, all China values, all CAMX values, India, and the IFI-implied
  margins of the Netherlands, Belgium and the UAE.
* *Lifecycle (Ember, IPCC technology factors)*: the **Belgium average (0.150) and
  the UAE average (0.468)**. Because Ember's figure includes upstream fuel supply and
  plant construction, it sits above a direct-emission average, which is conservative
  against electrification. Within the Belgian and UAE rows the average is therefore
  on a different basis from the two IFI-implied outer states.

The Netherlands is **not** an Ember row: its average is the Dutch official CBS
direct-emission figure (0.20 kg/kWh for 2024). Ember's lifecycle figure for the
Netherlands (0.254 in the earlier version; 253.56 g/kWh for 2025 in `atlas_ports.csv`)
is used only in the global atlas (Section 9).

To handle the boundary question the paper reports each factor's threshold position on
both boundaries: busbar versus tank-to-wheel, and delivered (grossed up by T&D
losses, `TD_LOSSES` in `src/experiments.py`) versus well-to-wheel diesel
(3.20 kg CO2/L). Only conclusions that agree on both are relied upon. `TD_LOSSES`
holds **India 0.17 and Netherlands 0.04 only**; every other regime (Belgium, the
three Chinese grids, California, UAE) falls back on a **uniform 0.10 placeholder**,
which is not a published figure for any of them. It is used only in the
alternative-boundary rows (`emission_boundary`, and the "delivered vs well-to-wheel"
rows of the threshold table).

### 1.2 Source of each factor

| Regime | Average | Marginal and cleanest |
|---|---|---|
| Netherlands | CBS, *Energie- en emissiefactoren elektriciteit, update 2024* (Dec 2025): "minimum van 0,20 kg/kWh" in 2024, integral method, direct emissions at generation | IFI TWG *Dataset of Default Grid Factors* v.2.0 (Jul 2019, UNFCCC PDF) combined margins 280 (intermittent) and 221 (firm) gCO2/kWh; OM 0.315 and BM 0.175 derived (Section 1.3). The IFI v3.2 values previously recorded (418 / 246) could not be confirmed verbatim from a public file and are no longer used |
| Belgium | Ember yearly data via Our World in Data (updated 2026-06-30): Belgium 2025 = 149.82 gCO2e/kWh (2024: 126.96). Lifecycle | IFI v3.2 combined margins 0.204 and 0.124 (EIB Table A1.3); derived |
| China (three grids) | MEE and NBS, Announcement 2025 No. 47 (published 31 Dec 2025), Table 2, 2023 regional average CO2 emission factors (Section 1.4) | NCSC (National Center for Climate Change Strategy and International Cooperation), *2024年减排项目中国区域电网二氧化碳基准线排放因子* (2024 edition; OM = weighted mean of 2020-2022 data): simple operating margin and build margin (Section 1.4). Supersedes the MEE 2019 edition |
| USA-California | US EPA eGRID2023 rev. 2 (12 Jun 2025), Table 1, CAMX total output CO2 rate (Section 1.5) | Marginal: CAMX non-baseload output CO2 rate (EPA's marginal proxy). Cleanest: zero, a physical bound |
| UAE | Ember yearly data, 2024 data year, 468 gCO2e/kWh (467.51 in `atlas_ports.csv`). Lifecycle; no official operational national average was located | IFI v.2.0 (Jul 2019, UNFCCC PDF) combined margins 522 (intermittent) and 353 (firm) gCO2/kWh; OM 0.623 and BM 0.220 derived. The IFI v3.2 values previously recorded (450 / 333) could not be confirmed verbatim from a public file and are no longer used |
| India | CEA, *CO2 Baseline Database* v22.0 (published August 2026; FY2025-26, Table S): weighted average 0.675 | CEA v22.0: simple operating margin 0.963 (marginal), build margin 0.446 (cleanest), combined margin 0.705 |

India's previous source, CEA v21.0 (FY2024-25: average 0.710, OM 0.961, BM 0.512, CM
0.736), is **superseded** by v22.0. India is the only regime for which the average, both
margins and the combined margin are all published as such; the three Chinese grids have
the average and both margins published by national authorities, but not a combined
margin. **Mapping the CEA build margin to "cleanest" and the operating
margin to "marginal" is our interpretation, not CEA's.** The CDM operating margin is
the generation-weighted average of non-must-run plant, not an hourly short-run
marginal, and the build margin is the intensity of recent additions, not a
renewable-rich hour. The same interpretation is applied to every regime. Ember's
lifecycle figure for India is 0.670 (670.13 g/kWh, `atlas_ports.csv`), about 1 %
below the CEA average; CEA is used because it publishes the margins. **India's average
now sits on the emission-neutral threshold**: the CEA v22.0 average 0.675 is 0.004
above the central busbar / tank-to-wheel threshold of 0.671 (Section 3), while Ember's
0.670 is just below it, so which side of the threshold India's average grid falls on
depends on the source.

### 1.3 How the IFI-implied operating and build margins were derived

The Netherlands, Belgium and the UAE have no published national operating or build
margin in the sources reached. The IFI (International Financial Institutions)
Technical Working Group's harmonised dataset publishes, per country, **two combined
margins** (CM). The Netherlands and the UAE use the *Dataset of Default Grid Factors*
v.2.0 (July 2019, UNFCCC PDF); Belgium uses v3.2 (April 2022) as reproduced by EIB
Table A1.3. Each pair consists of one CM for *intermittent* (wind and solar)
projects, weighted 75 % operating margin (OM) and 25 % build margin (BM), and one
for *firm* generation or electricity consumption, weighted 33 % OM and 67 % BM
(IFI TWG, *GHG Accounting for Grid Connected Renewable Energy Projects*, v02.0,
July 2019). The two published combined margins are two linear equations in the two
unknowns OM and BM:

    CM_int  = 0.75 OM + 0.25 BM
    CM_firm = 0.33 OM + 0.67 BM

so that, with 0.42 = 0.75 x 0.67 - 0.25 x 0.33,

    OM = (0.67 CM_int  - 0.25 CM_firm) / 0.42
    BM = (0.75 CM_firm - 0.33 CM_int ) / 0.42  =  (CM_int - 0.75 OM) / 0.25

| Country | IFI version | CM_int | CM_firm | OM (marginal state) | BM (cleanest state) |
|---|---|---|---|---|---|
| Netherlands | v2.0 (2019) | 0.280 | 0.221 | 0.3151 -> **0.315** | 0.1746 -> **0.175** |
| Belgium | v3.2 (2022), via EIB | 0.204 | 0.124 | 0.2516 -> **0.252** | 0.0611 -> **0.061** |
| UAE | v2.0 (2019) | 0.522 | 0.353 | 0.6226 -> **0.623** | 0.2202 -> **0.220** |

**Superseded inputs.** The IFI v3.2 combined margins previously recorded for the
Netherlands (418 / 246 gCO2/kWh, which gave OM 0.520 and BM 0.111) and the UAE
(450 / 333, which gave OM 0.520 and BM 0.241) could not be confirmed verbatim from a
public file (the public EIB PDF text is truncated before these rows and repeated
retrievals disagreed). They are **no longer used**; `grid_factor_sources.csv` keeps
them marked "NOT USED".

The recorded combined margin is the firm one (0.221, 0.124, 0.353). The inputs are
rounded to whole g/kWh, so OM and BM are good to roughly 1 g/kWh. Both published
combined margins are reproduced exactly by construction (two equations, two
unknowns); the derivation is therefore not a check on the IFI dataset. A 50/50
weighting would give a negative Belgian BM, which supports the 33/67 reading. The
IFI definitions differ from the CDM ones: IFI's OM is the costliest 50 % of fossil
generation (three-year rolling IEA data) and its BM the average intensity of new
generation projected over eight years under the IEA WEO Stated Policies Scenario
(IFI TWG methodological note). The Netherlands and UAE pairs are read from the
published IFI v2.0 PDF, which gives combined margins only. **The IFI v3.2 spreadsheet
itself was not opened** (downloads from unfccc.int were blocked); Belgium's pair comes
from EIB's reproduction in Table A1.3. In all three cases the combined margins are
published and the operating and build margins are derived from them, not published.

### 1.4 China: MEE regional averages 2023 and NCSC 2024 operating and build margins

Regional grids: North China = Beijing, Tianjin, Hebei, Shanxi, Shandong, western
Inner Mongolia; East China = Shanghai, Jiangsu, Zhejiang, Anhui, Fujian; Southern
China = Guangdong, Guangxi, Yunnan, Guizhou, Hainan.

| Grid | Average, 2023 (MEE/NBS Table 2) | Operating margin (NCSC 2024 ed.) | Build margin (NCSC 2024 ed.) | Combined (equal weight) | Corridors |
|---|---|---|---|---|---|
| East (华东) | 0.5500 | 0.7782 | 0.1951 | 0.487 | Shanghai, Ningbo |
| North (华北) | 0.6361 | 0.9531 | 0.3095 | 0.631 | Qingdao, Tianjin |
| Southern (南方) | 0.4042 | 0.7906 | 0.1816 | 0.486 | Shenzhen |

Superseded margins (MEE 2019 edition, published 29 Dec 2020; previously used, now
replaced and kept in `grid_factor_sources.csv` for the record only), OM / BM: East
0.7921 / 0.3870, North 0.9419 / 0.4819, Southern 0.8042 / 0.2135 (equal-weight combined
0.590, 0.712, 0.509).

* **Averages.** Ministry of Ecology and Environment and National Bureau of
  Statistics, Announcement 2025 No. 47 (published 31 Dec 2025), *2023 national and
  regional electricity average CO2 emission factors*. These are location-based
  factors for electricity consumed, including market-traded non-fossil electricity
  (Table 1-3 basis), direct CO2. National 2023: 0.5306; national excluding
  market-traded non-fossil 0.6096; national fossil-only 0.8273. The 2022 edition
  (Announcement 2024 No. 33) gave North 0.6776, East 0.5617, Southern 0.3869
  (national 0.5366). Provincial 2023 values, recorded in `grid_factor_sources.csv`
  but not used by the model: Shanghai 0.5737, Zhejiang 0.4974, Tianjin 0.6796,
  Shandong 0.6191, Guangdong 0.4419. The model uses the **regional** value for each
  port because the grid is regional.
* **Margins.** NCSC (National Center for Climate Change Strategy and International
  Cooperation, issuing for MEE), *2024年减排项目中国区域电网二氧化碳基准线排放因子*
  (2024 edition), Table 3: simple operating margin ("OM为2020-2022年电量边际排放因子的加权平均值",
  i.e. the weighted mean of 2020-2022 data) and build margin, direct CO2, operational
  basis. Mapped to marginal and cleanest states. This edition **supersedes** the MEE
  2019 edition (*2019年度减排项目中国区域电网基准线排放因子*, data of 2015-2017) used
  in an earlier draft; the 2019 edition is not the latest and is no longer a model input.
* **Combined.** NCSC publishes no combined margin. The model records the
  **equal-weight blend** of the published OM and BM (the CDM/CCER default):
  (0.7782 + 0.1951)/2 = 0.487, (0.9531 + 0.3095)/2 = 0.631, (0.7906 + 0.1816)/2 = 0.486.
  This is a computed value, not a published one.
* **Vintage.** The average is the 2023 edition and the operating margin rests on
  2020-2022 data, so the two are now close in vintage; the earlier mismatch with the
  2019 edition (data of 2015-2017) no longer applies.

### 1.5 USA-California: eGRID2023, subregion CAMX

US EPA, eGRID2023 summary tables (rev. 2, 12 Jun 2025), Table 1, subregion output
emission rates, converted at 0.000453592 kg/lb:

* **Average 0.194**: CAMX total output CO2 rate, 428.5 lb/MWh = 0.1943 kg/kWh.
* **Marginal 0.435**: CAMX non-baseload output CO2 rate, 958.3 lb/MWh = 0.4347
  kg/kWh. This is EPA's marginal *proxy*, not a CDM operating margin.
* **Cleanest 0.000**: **a physical lower bound, not a published factor.** eGRID
  publishes no build margin; the cleanest state is set to zero, the emission rate of
  renewable output that would otherwise be curtailed in surplus hours.
* No combined margin is carried for California.

For reference the same table gives the US national average 0.348 (767.2 lb/MWh) and
non-baseload 0.6226 (1,372.5 lb/MWh); these are not used by the model. Direct
combustion CO2, no T&D losses.

### 1.6 Other grid input and its source

* Indian combined margin 0.705 = equal-weight blend of 0.963 and 0.446 as published
  by CEA (v22.0). The v21.0 combined margin 0.736 is superseded.
* IPCC AR5 lifecycle medians are no longer used for outer states (they were in the
  earlier version).
* `grid_factor_sources.csv` also records IFI v2.0 (2019) combined margins. Those for
  the **Netherlands (0.221 firm, 0.280 intermittent) and the UAE (0.353, 0.522) are
  model inputs** (Section 1.3). Those for Belgium (0.165, 0.227), China (0.494, 0.775),
  the USA (0.285, 0.418) and India (0.673, 0.878) are recorded for reference and are
  **not** model inputs (Belgium uses v3.2).

### 1.7 How the three states are weighted

The scenario tree is built so that **the expected emission factor equals the published
average exactly**, for every regime. Mass `OUTER_MASS = 0.50` (`src/instance.py`)
goes on the two outer states together and 0.50 on the average; the split inside the
outer pair is solved:

    p_clean + p_marginal = 0.50,   p_clean ef_clean + p_marginal ef_marginal = 0.50 ef_average
    => p_clean = 0.50 (ef_average - ef_marginal) / (ef_clean - ef_marginal)

Resulting probabilities (computed from the table in Section 1.1; also recorded in
each instance's metadata):

| Regime | p(clean) | p(average) | p(marginal) |
|---|---|---|---|
| Netherlands | 0.411 | 0.50 | 0.089 |
| Belgium | 0.267 | 0.50 | 0.233 |
| China-East | 0.196 | 0.50 | 0.304 |
| China-North | 0.247 | 0.50 | 0.253 |
| China-South | 0.318 | 0.50 | 0.182 |
| USA-California | 0.277 | 0.50 | 0.223 |
| UAE | 0.192 | 0.50 | 0.308 |
| India | 0.279 | 0.50 | 0.221 |

The same scaling is applied to the electricity-price multipliers (Section 2). Two
candours. First, the Netherlands' average (0.200) lies close to its derived cleanest
state (0.175), so most of its outer mass falls on the clean state and its marginal
state carries under 0.09 probability. Second, because the outer states are derived or
interpreted (Sections 1.3-1.5), they are the least authoritative numbers in the file:
the Netherlands' 0.175 and 0.315 and the UAE's 0.220 and 0.623 are derived from
2019-vintage IFI v2.0 combined margins under IFI weights that we could not check
against the IFI spreadsheet.

---

## 2. Energy prices

| Regime | Business electricity (USD/kWh) | Electricity source | Diesel (USD/L) | Diesel source (local) | `fx_per_usd` |
|---|---|---|---|---|---|
| Netherlands | 0.220 | GlobalPetrolPrices (GPP) international comparison of business electricity prices (multi-year average series) | 2.170 | GPP 9 Feb 2026, EUR 1.82/L | 0.839 EUR |
| Belgium | 0.277 | GPP, June 2025: EUR 0.233/kWh | 1.950 | GPP 9 Feb 2026, EUR 1.64/L | 0.924 EUR |
| China-East | 0.105 | Shanghai industrial and commercial tariff, 1-10 kV, standard period, May 2025: CNY 0.755/kWh (China Briefing compilation of grid-company tariffs) | 0.930 | GPP Feb 2026, CNY 6.41/L | 7.19 CNY |
| China-North | 0.108 | Mean of Tianjin (CNY 0.833) and Shandong (CNY 0.716) tariffs, same basis | 0.930 | as above | 7.19 CNY |
| China-South | 0.113 | Guangdong tariff, CNY 0.811/kWh, same basis | 0.930 | as above | 7.19 CNY |
| USA-California | 0.264 | US EIA, California commercial-sector average price, 2025: 26.36 US cents/kWh | 1.281 | US EIA, California No. 2 diesel retail, 2025 annual average USD 4.850/gal | 1.0 USD |
| UAE | 0.110 | GPP, June 2025: AED 0.405/kWh | 0.780 | GPP 8 Dec 2025, AED 2.85/L | 3.6725 AED |
| India | 0.122 | GPP international comparison (multi-year average); the India country page quotes 0.116 for June 2025, about 5 % lower | 1.060 | Goodreturns/PPAC retail, Indian metros 9 Sep 2026 (INR 97.8-103.8/L); GPP 9 Mar 2026 INR 90.58/L | 92.43 INR |

* **The electricity prices are not one series.** NL and India use the GPP
  comparison table; Belgium, UAE a GPP June 2025 single-quarter business price;
  China regional tariffs from a China Briefing compilation (May 2025, Shanghai, Tianjin,
  Shandong and Guangdong as proxies for the three grids); California the EIA 2025 annual
  commercial-sector average. All are business tariffs at the meter, comparable in
  kind but not to the cent.
* **California electricity (0.264).** The 26.36 cents/kWh was not read from eia.gov
  (503 on retrieval); two independent relays of EIA data agree on it. The official
  2024 value is 25.54 cents/kWh (EIA Electric Power Annual, Table 2.10).
* **India diesel.** USD 1.06/L corresponds to about INR 98/L, the Mumbai price, the metro
  served by the JNPT corridor.
* **Diesel dates** run from 8 December 2025 to 9 September 2026 because sources
  update countries on different cycles; the dates are recorded per row.
* **Currency.** GPP local prices are converted at the USD value GPP reports beside
  them at retrieval (EIA prices are already USD). The `fx_per_usd` column is
  documentation only: it records a rate for redoing the conversion and is **not used in
  any computation** (Section 8.3); see Section 8.2 for rows where it does not
  reproduce the stated USD prices.
* **State multipliers.** Within a scenario the electricity price is the national
  price times a state factor of **0.80 (clean), 1.00 (average), 1.55 (marginal)**
  (`GRID_STATES`), rescaled by one factor per regime so that the expected multiplier is
  1 under the state probabilities of Section 1.7, i.e. the expected price is the
  published price. The multipliers are **calibrated, not published**.

---

## 3. Vehicle technology and carbon price (`parameters.csv`)

| Parameter | Value | Range tested | Source |
|---|---|---|---|
| `e_elec`, electric traction energy **at the battery** | 1.25 kWh/km | 1.15-1.45 | Le Corguille, Hacker and Dolinga (2025), *Real-world data analysis of battery electric trucks operating in Germany*, EVS38: 19 vehicles, 807 driving events, Sept 2023 - Jan 2025; fleet mean 0.96 kWh/km at a mean gross combination weight of 20.4 t over an 11-40 t range, rising 0.18 kWh/km per additional 10 t; measured at the vehicle, **excluding charging losses** |
| `charger_efficiency`, grid to battery | 0.92 | 0.88-0.95 | AC and DC fast charging including rectifier and battery-side losses; 0.92 is a mid-range DC value (calibrated) |
| Grid-side electric energy (derived) | 1.25 / 0.92 = **1.359 kWh/km** | 1.21-1.65 | the two rows above combined (lower bound 1.15/0.95, upper 1.45/0.88); this is the epsilon the model uses |
| `f_diesel`, diesel consumption | 0.340 L/km | 0.300-0.380 | Heavy tractor-semitrailer motorway consumption of 30-38 L/100 km (EcoTransIT World Methodology Update 2024; ICCT heavy-duty fleet data); mid-point for a laden 40 t combination |
| `platoon_saving` | 0.055 of traction energy | 0.030-0.070 | NACFE *Confidence Report: Two-Truck Platooning*: lead truck about 4 %, following truck about 10 %, two-truck track average about 7 % at a 40-50 ft gap, with a recommended derate of about one quarter |
| `platoon_share_cap` | 0.75 of trucks on an arc | 0.50-0.95 | Largest share of an arc's trucks that can be matched; NACFE's derate assumes about three quarters of running time in platoon (calibrated) |
| `ef_diesel_ttw` | 2.680 kg CO2/L | 2.640-2.700 | Tank-to-wheel factor (EcoTransIT World Methodology Update 2024; UK DESNZ/DEFRA) |
| `ef_diesel_wtw` | 3.200 kg CO2/L | 3.100-3.300 | Well-to-wheel, about +19 % (EcoTransIT World Methodology Update 2024) |
| `scc`, carbon price | 0.190 USD/kg CO2 | 0.120-0.340 | US EPA (2023) *Report on the Social Cost of Greenhouse Gases*, Table ES.1, 2020 emissions: USD 120, 190 and 340 per tonne at 2.5 %, 2.0 % and 1.5 % near-term Ramsey rates |
| `c_platoon` | 2.00 USD/truck-arc | 0.50-8.00 | Matching delay, gap-keeping telematics, dispatch overhead (calibrated) |
| `charger_module_kwh` | 2,000 kWh/day per bay | -- | One 350 kW bay at about 6 h/day and 95 % availability |
| `charger_capex` | 26,000 USD/yr per bay | 18,000-40,000 | 350 kW public heavy-duty bay with grid connection, 10 years at 8 % |
| `electrify_capex_fixed` | 120,000 USD/yr per arc | 80,000-200,000 | Site, HV connection and substation works, 15 years at 8 % |
| `electrify_capex_km` | 900 USD/yr per km | 600-1,400 | Distance-proportional charging-site component (about one site per 100 km at about USD 1.0 M capital); not medium-voltage line |
| `grid_stress_weight` | 0.020 USD/kWh | 0.000-0.060 | Shadow value of peak grid load (network-reinforcement deferral) |
| `unmet_penalty` | 900 USD/container | 400-2,000 | Demurrage, detention and lost margin on a failed delivery |
| `circuity` | 1.12 | 1.00-1.40 | Lead-case (Rotterdam) circuity; every corridor uses its own fitted value from `ports.csv` (Section 4), and the sweep runs from 1.00 (straight line) to 1.40 |
| `wage` | 1.204 USD/km | 0.602-2.408 | Lead-case (Rotterdam, Netherlands) haulage cost excluding fuel (CNR 2024, Section 7); every corridor uses its own regime value from `energy_regimes.csv`, and the sensitivity sweep and the haulage-neutrality check halve and double each corridor's own cost (the range shown is the lead case's) |

**Derivation of the electric consumption figure.** Two anchors at the 40 t gross
weight of a container tractor-semitrailer: (a) the study's regression,
0.96 + 0.18 x (40 - 20.4)/10 = 1.31 kWh/km; (b) the same study's 38 t long-haul
reference case of 1.15 kWh/km over 4,439 km, adjusted to 40 t by the same gradient,
1.19 kWh/km. The model takes 1.25 between them; the 1.15-1.45 range spans the lower
anchor to the regression value plus its residual spread, and is not a weight band.
The figure is battery-side, while the model's charging capacity, emissions, charge
revenue and grid stress refer to energy metered at the corridor's chargers, hence the
division by 0.92.

**Platooning.** NACFE's real-world figure of about 4 % is reproduced by the product of
the saving (7 % less the derate, 5.5 %) and the platoonable-share cap (0.75): 5.5 % x
0.75 = 4.1 %. The 10 % often quoted is the following truck alone.

**Emission-neutral grid factor (computed from the rows above, as in `src/experiments.py`).**
Electrification lowers CO2 per km only if the grid factor is below
`f_diesel x ef_diesel / (e_elec / charger_efficiency)`:

| Boundary | Central | Interval (low-high over all inputs) |
|---|---|---|
| Busbar vs tank-to-wheel diesel (2.68 kg/L) | **0.671** | 0.481-0.848 |
| Delivered vs well-to-wheel diesel (3.20 kg/L) | **0.801** | 0.564-1.036 |

Comparing grid and diesel factors per kWh instead of per kilometre is a unit error
that reverses the result: a diesel truck burns 0.34 L/km, about 3.4 kWh of fuel energy,
for what an electric truck does with 1.36 kWh of metered grid energy.

**Carbon price.** USD 190 per tonne CO2 (0.19 USD/kg). EPA's table is in **2020
dollars** while prices, wages and capital costs here are 2025-26 figures; the SCC is
not rebased, which understates it on a consistent basis. The sensitivity sweep runs
from 0 to 0.80 USD/kg, well past plausible rebasing, and the paper reports the carbon
price at which each conclusion changes.

**Structural constants** (`src/instance.py`; modelling choices recorded in each
instance's metadata, not measurements):

| Constant | Value | Meaning |
|---|---|---|
| `OPERATING_DAYS` | 250 | working days a year the corridor is modelled over |
| `HEADROOM_FRACTION` | 0.75 | clean-state charging headroom as a fraction of the energy full electrification at mean demand needs |
| grid headroom multipliers | 1.00 / 0.80 / 0.45 | clean / average / marginal |
| `ARC_CAP_MULTIPLE` | 4.0 | arc truck-movement capacity as a multiple of peak daily boxes |
| `OUTER_MASS` | 0.50 | probability mass on the two outer grid states together |
| price shape | 0.80 / 1.00 / 1.55 | clean / average / marginal, rescaled (Section 2) |
| `DEMAND_LEVELS`, `DEMAND_PROBS` | 0.80 / 1.00 / 1.30 and 0.30 / 0.40 / 0.30 | low, mid, high |
| `SHARE_DIRICHLET` | 6.0 | concentration of the carrier size split |
| `TILT_DIRICHLET` | 8.0 | concentration of the node tilt at zero heterogeneity; the tilt concentration is max(0.25, 8.0 x (1 - heterogeneity)), 3.6 at the default heterogeneity 0.55 |
| `PROCUREMENT_STEPS` | 127 | charging procurement steps spanned per corridor; fixes the hub size |

The hub size (bays per procurement unit, `bays_per_hub`) from `build_instance(<corridor>)`
at default arguments: Rotterdam 19, Antwerp 14, Shanghai 81, Ningbo 98, Qingdao 121,
Tianjin 72, Shenzhen 52, San Pedro Bay 75, Jebel Ali 11, JNPT 25. The hub is sized so that the same
number of procurement steps spans each corridor's grid headroom, which keeps the
model's size independent of corridor volume.

**Where the inputs are used** (`src/experiments.py`, all ten corridors unless stated):
`corridor_verdicts` (first best, all-diesel, uncharged plan, emission decomposition);
`split_ensemble` (Section 6); `haulage_neutrality` (Section 7); `lifetime_thresholds`
(12-year vehicle life, average and operating-margin factors against the tank-to-wheel
threshold); `global_atlas` (Section 9); `reach_across` (Tianjin, San Pedro Bay and
JNPT only; families F0 and F4).

---

## 4. Corridors, nodes and road distances

Node coordinates are published WGS84 positions (mostly Wikipedia city pages; the port
points are terminal or gate positions, see `node_coordinate_sources.csv`). Arc lengths
are **derived**: the great-circle distance between the endpoints times a
per-corridor **circuity factor** (`circuity` in `ports.csv`), unless the arc carries a
published `road_km`, which overrides it.

**The circuity factor is fitted, not validated.** One factor per corridor is chosen
so that a single reference route reproduces its published driving distance
(`circuity_check`); reproducing that distance afterwards is circular, so the table
reports the reference route and its residual. Individual arcs can be much further out.

| Corridor | Circuity | Reference route | Published | Great circle | Residual of fitted rule |
|---|---|---|---|---|---|
| Rotterdam | 1.12 | Maasvlakte to Venlo via A15/A16/A58/A67 | about 180 km | 187.0 km is the *derived* length | +3.9 % |
| Antwerp | 1.075 | E313 Antwerp-Liege | 112 km (the same source also gives 130 km, ratio 1.25) | 104.2 km | 0.0 % |
| Shanghai | 1.10 | G42 Huning Expressway, Zhenru to Maqun, termini | 274 km | about 250 km | +0.4 % |
| Ningbo | 1.16 | Ningbo to Yiwu by G1512/G15 (Rome2rio) | about 181 km | 156.0 km | 0.0 % (the same arc carries `road_km` = 181) |
| Qingdao | 1.19 | Qingdao to Jinan by G20 (Rome2rio) | about 366 km | 308.4 km | +0.3 % |
| Tianjin | 1.07 | Tianjin to Beijing by G2 (Rome2rio) | about 118 km | 110.4 km | +0.1 % |
| Shenzhen | 1.14 | Guangshen Expressway, Guangzhou to Shenzhen Huanggang | 122.8 km | 107.5 km | -0.2 % |
| San Pedro Bay | 1.18 | Los Angeles to Las Vegas by I-15 | about 435 km | 367.6 km | -0.3 % |
| Jebel Ali | 1.14 | Dubai to Abu Dhabi by E11 | about 140 km | 122.9 km | +0.1 % |
| JNPT | 1.20 | Mumbai-Pune Expressway, Kalamboli to Kiwale | 94.5 km | 79.0 km | +0.3 % |

Notes on the reference routes:

* **Rotterdam** (lead). The reference route runs port - Waalhaven - Moerdijk -
  Tilburg - Eindhoven - Venlo and sums to 187.0 km derived against about 180 km
  published. It is the only reference that overshoots by more than 1 %.
* **Antwerp.** Published length 112 km against 104.2 km great circle between the
  junction and Liege (circuity 1.075).
* **Shanghai.** G42's 274 km runs between termini (Zhenru and Maqun), about 250 km
  apart on a great circle. The port node is at Waigaoqiao, though about half of
  Shanghai's volume is handled at Yangshan.
* **Ningbo, Qingdao, Tianjin.** Road distances are from the Rome2rio route
  planner, a routing estimate rather than an authority's measurement.
* **Shenzhen.** Reference endpoints are the expressway's termini, not exactly the
  node coordinates.
* **San Pedro Bay.** The reference is the long desert run to Las Vegas; the
  dense Inland Empire legs are short and may carry different circuity.
* **Jebel Ali.** Dubai-Abu Dhabi is the busiest axis; the legs to Al Ain and the
  mountain crossing to Fujairah (E88) are derived at the same coastal-motorway
  factor and are probably understated.
* **JNPT.** The reference is the expressway section from Kalamboli, not a
  port-access leg; the port-access leg is derived.

**Which arc lengths are published.** Two arcs carry `road_km`:

| Arc | Great circle | Fitted rule | Published road | Implied circuity |
|---|---|---|---|---|
| Rotterdam: Venlo to Duisburg (A67/A40) | 41.5 km | 46.5 km | **75 km** | 1.8 |
| Ningbo: Ningbo to Yiwu (G1512) | 156.0 km | 181 km | **181 km** (Rome2rio) | 1.16 |

Of the ten corridors' total modelled length of about 8,100 km, about 256 km (3 %) is
published; every other arc is derived from coordinates and a fitted scalar. Totals by
corridor (arcs, km): Rotterdam 9 / 447 (75 km published, 17 %); Antwerp 10 / 613;
Shanghai 10 / 673; Ningbo 8 / 883 (181 km published, 21 %); Qingdao 9 / 1,107; Tianjin
8 / 830; Shenzhen 8 / 448; San Pedro Bay 9 / 1,318; Jebel Ali 9 / 628; JNPT 11 / 1,156.
The circuity sweep (1.00 to 1.40) rescales all arcs together and so cannot probe the
patterned error of a single factor (it understates port-access, mountain and
detour legs and overstates flat motorway legs); a deployment version should take arc
lengths from a routing engine.

**Rotterdam (lead corridor) arcs** (`networks/rotterdam_arcs.csv`):

| Arc | Highway label | Km | Great circle | Source |
|---|---|---|---|---|
| Maasvlakte - Waalhaven | A15 | 29.09 | 25.97 | derived |
| Waalhaven - Moerdijk | A16 | 29.15 | 26.03 | derived |
| Moerdijk - Tilburg | A58 | 40.87 | 36.49 | derived |
| Tilburg - Eindhoven | A58 | 32.59 | 29.10 | derived |
| Eindhoven - Venlo | A67 | 55.31 | 49.38 | derived |
| Venlo - Duisburg | A40 | 75.00 | 41.53 | published |
| Waalhaven - Utrecht | A12 | 58.79 | 52.49 | derived |
| Utrecht - Nijmegen | A12/A50 | 64.95 | 57.99 | derived |
| Nijmegen - Venlo | A73 | 60.87 | 54.35 | derived |

**Nodes** (`networks/<corridor>_nodes.csv`; demand weight and export share in
brackets; every demand node is an electrifiable-network node and every arc has
`electrifiable = 1`):

| Corridor | Port node | Junction(s) | Arcs | Km | Demand nodes (weight, export share) |
|---|---|---|---|---|---|
| Rotterdam | Rotterdam Maasvlakte | Rotterdam Waalhaven | 9 | 447 | Moerdijk (0.022, 0.55), Tilburg (0.133, 0.50), Eindhoven (0.149, 0.48), Venlo (0.061, 0.62), Duisburg (0.302, 0.65), Nijmegen (0.106, 0.52), Utrecht (0.227, 0.40) |
| Antwerp | Antwerp Deurganck dock (left bank) | Antwerp R1 ring / Kennedy tunnel; Lummen E313/E314 interchange | 10 | 613 | Ghent (0.081), Lille FR (0.071), Brussels (0.373), Charleroi (0.061), Genk (0.020), Liege (0.059), Cologne DE (0.305), Venlo NL (0.030); export share 0.45 at every node |
| Shanghai | Shanghai Waigaoqiao | Shanghai Jiading | 10 | 673 | Kunshan (0.038, 0.62), Suzhou (0.192, 0.62), Wuxi (0.134, 0.60), Changzhou (0.095, 0.58), Nanjing (0.168, 0.50), Jiaxing (0.097, 0.60), Hangzhou (0.215, 0.55), Huzhou (0.061, 0.58) |
| Ningbo | Ningbo-Zhoushan (Beilun) | none | 8 | 883 | Ningbo (0.160), Shaoxing (0.090), Hangzhou (0.205), Huzhou (0.057), Yiwu/Jinhua pref. (0.120), Taizhou (0.113), Wenzhou (0.163), Jiaxing (0.092); export share 0.55 at every node |
| Qingdao | Qingdao Qianwan | Jiaozhou | 9 | 1,107 | Qingdao (0.154), Weifang (0.144), Zibo (0.072), Jinan (0.141), Yantai (0.109), Linyi (0.168), Jining (0.128), Tai'an (0.084); export share 0.55 |
| Tianjin | Tianjin Port (Xingang/Dongjiang) | none | 8 | 830 | Tianjin (0.167), Langfang (0.066), Beijing (0.262), Tangshan (0.093), Cangzhou (0.088), Baoding (0.139), Shijiazhuang (0.135), Zhangjiakou (0.050); export share 0.55 |
| Shenzhen | Shenzhen Yantian (YICT) | none | 8 | 448 | Shenzhen (0.236), Dongguan (0.141), Guangzhou (0.252), Foshan (0.128), Zhongshan (0.059), Jiangmen (0.065), Huizhou (0.081), Heyuan (0.038); export share 0.55 |
| San Pedro Bay | San Pedro Bay (LA-Long Beach) | Commerce I-710/I-5 | 9 | 1,318 | City of Industry (0.450), Ontario (0.033), Moreno Valley (0.109), San Bernardino (0.033), Barstow (0.033), Las Vegas (0.102), Bakersfield (0.041), Phoenix (0.199); export share 0.35 |
| Jebel Ali | Jebel Ali Port | none | 9 | 628 | Dubai Al Quoz (0.202, 0.35), Sharjah Industrial (0.192, 0.35), Ajman (0.058, 0.30), Ras Al Khaimah (0.020, 0.45), Abu Dhabi Mussafah (0.224, 0.30), Al Ain (0.090, 0.25), Fujairah (0.012, 0.30), Dubai Industrial City (0.202, 0.40) |
| JNPT | Nhava Sheva | Kalamboli | 11 | 1,156 | Bhiwandi (0.258, 0.30), Chakan-Talegaon (0.111, 0.55), Pune (0.111, 0.50), Nashik (0.143, 0.55), Aurangabad (0.087, 0.60), Ahmednagar (0.107, 0.45), Vapi (0.040, 0.65), Surat (0.143, 0.60) |

Highway labels are the author's assignment of the route a link follows, not source-checked
link by link; they appear in the study-area figures, where a reader will read them as route
evidence. Labels flagged as least certain in the research notes include the
Tianjin G25, G18, G4 and G6 links. The **export share** (`exp_share`) is not
published for any node: it encodes the directional imbalance behind empty
repositioning and is an **assumption** (Section 8).

**Coordinate sources.** `node_coordinate_sources.csv` documents coordinates for the six
corridors added most recently (Antwerp, Ningbo, Qingdao, Tianjin, Shenzhen, San Pedro
Bay). San Pedro Bay's port point is recorded as copied from an earlier file and
"not re-sourced". Rotterdam, Shanghai, Jebel Ali and JNPT coordinates, and the
Commerce junction, have no row in that file.

---

## 5. Throughput and road volume

Road boxes per day (`daily_boxes`, `src/instance.py`):

    daily boxes = TEU x (1 - transshipment share) x road share / (TEU per truck) / 250

The road share applies to **hinterland** throughput, since transshipped boxes never
touch a road. All ten corridors assign the whole of their port's road volume to their
7-8 demand nodes (Section 6).

| Corridor | Container throughput | Transshipment share | Road share | TEU per truck | Road boxes/day |
|---|---|---|---|---|---|
| Rotterdam | 14.2 M TEU (2025) | 0.30 **calibrated** | 0.59 **published** (hinterland modal split 2022: road 59 %, barge 30 %, rail 11 %; BALM report as cited by UIRR) | 1.68 cal. | 13,963 |
| Antwerp-Bruges | 13.63 M TEU (2025) | 0.25 cal. | 0.55 cal. (no reliable current container modal split located) | 1.65 cal. | 13,630 |
| Shanghai | 55.06 M TEU (2025) | 0.144 **published** (international transshipment 7.911 M TEU) | 0.45 cal. | 1.60 cal. | 53,023 |
| Ningbo-Zhoushan | 43.87 M TEU (2025) | 0.20 cal. (incl. water-to-water) | 0.70 cal. | 1.60 cal. | 61,418 |
| Qingdao | 32.89 M TEU (2025) | 0.20 cal. | 0.85 cal. | 1.60 cal. | 55,913 |
| Tianjin | 24.03 M TEU (2025) | 0.10 cal. | 0.88 cal. | 1.60 cal. | 47,579 |
| Shenzhen | 35.41 M TEU (2025) | 0.15 cal. | 0.75 **derived** from latest published shares (2022 barge-based "combined port" about 24 %, sea-rail about 0.7 %) | 1.60 cal. | 56,435 |
| San Pedro Bay | 20,120,913 TEU (2025): Los Angeles 10,239,318 + Long Beach 9,881,595 | 0.00 (negligible) | 0.74 **derived** from the published 26 % of Port of Los Angeles cargo on on-dock rail | 1.75 cal. (predominance of 40-ft boxes) | 34,033 |
| Jebel Ali | 15.55 M TEU (2025; DP World FY2025) | 0.50 cal. | 0.95 cal. | 1.60 cal. | 18,466 |
| JNPT | 7.3 M TEU (FY2024-25) | 0.03 cal. | 0.85 **derived** from published rail volume (1,078,315 TEU, 14.8 % of throughput) | 1.55 cal. | 15,533 |

"cal." = calibrated; **published** or **derived** as marked. Throughput is a published
measurement in every row; the rows' sources are in Section 10 and the `source` column
of `ports.csv`.

What is published and what is calibrated among the three shares:

* **Transshipment share.** Published only for **Shanghai** (14.4 %). Calibrated for
  every other corridor; Jebel Ali's 0.50 is a calibration for a major Gulf hub whose
  share is not published, and Rotterdam's 0.30 is at the low end of commonly
  quoted shares (the port's 2025 release reports transshipment and hinterland
  volume changes but no share). San Pedro Bay is taken as negligible.
* **Road share.** **Published** for Rotterdam (the 2022 modal split is for
  containers, a vintage three years before the throughput). **Derived from a
  published figure** for JNPT (the rail share is taken of total throughput, not
  hinterland throughput; at 3 % transshipment the difference is under one percentage
  point), San Pedro Bay (Los Angeles on-dock rail share applied to the whole bay) and
  Shenzhen (2022 shares). **Calibrated** for Antwerp, Shanghai, Ningbo, Qingdao,
  Tianjin and Jebel Ali. Shanghai's 0.45 reflects the large share of boxes moving by
  Yangtze and canal barge and is the most consequential calibrated share, because it
  multiplies the second-largest throughput. Sea-rail volumes recorded in `ports.csv`
  (Shanghai 1 M TEU, Ningbo above 2.0 M TEU, Qingdao 2.625 M TEU January-November 2025,
  Tianjin a 2025 forecast of 1.5 M TEU) are context, not model inputs.
* **TEU-per-truck factor.** Calibrated everywhere.

These three enter the model only through the daily box count, so a change in any of
them rescales every node's demand uniformly rather than changing its composition. The
sensitivity analysis tests that claim rather than asserting it.

**Hinterland coverage.** Each network assigns all its port's road volume to a handful
of nodes. Where the real hinterland is much wider than the network (Rotterdam's reach
across Germany, Belgium, France and Switzerland; the 53,000 to 61,000 boxes a day of
the three Yangtze- and Zhejiang-delta and Shandong corridors), arc volumes are inflated
relative to reality, and not symmetrically across corridors. The ten corridors are
comparable as modelling objects of similar structure, not as equally complete
representations of their hinterlands.

---

## 6. Demand allocation

### 6.1 Across nodes: population rule

No public source reports container volumes by hinterland node. The stand-in rule is
**population-proportional**: a node's share of its corridor's road volume,
`demand_weight` in `networks/<corridor>_nodes.csv` (rounded to three decimals), equals
its population divided by the sum of the populations of the corridor's demand nodes
in `node_populations.csv`. The weights reproduce the populations to within 0.001 for
every node of every corridor (the differences are rounding and, for a few nodes,
a slightly different population vintage). The model normalises the weights to sum to one
(`build_instance`). **No node's weight is reduced for barge or rail**: an earlier version
did so for Duisburg and no longer does (Duisburg carries 30 % of the Rotterdam
corridor's road volume at its city population).

Population basis and source, from `node_populations.csv`:

| Corridor | Basis | Vintage | Source |
|---|---|---|---|
| Rotterdam | Municipality (Duisburg: kreisfreie Stadt) | 2021-01 to 2026-01-01 depending on province | Wikipedia municipality pages |
| Antwerp | Municipality / commune; Brussels = Brussels-Capital Region (1,249,597); Cologne kreisfreie Stadt | 2023 to 2025-12-31 | Wikipedia lists and city pages |
| Shanghai, Ningbo | Prefecture-level city, 2020 census | 2020 | citypopulation.de (Jiangsu, Zhejiang pages); Wikipedia for Kunshan |
| Qingdao | Prefecture-level city, 2020 census | 2020 | citypopulation.de (Shandong); Wikipedia for Qingdao and Jinan |
| Tianjin | Prefecture-level city / municipality, 2020 census | 2020 | citypopulation.de (Hebei); Wikipedia for Tianjin and Beijing |
| Shenzhen | Prefecture-level city, 2020 census (Shenzhen: Wikipedia rounded 17,560,000) | 2020 | Wikipedia city pages |
| San Pedro Bay | **County**, 2020 Census | 2020 | US Census Bureau QuickFacts |
| Jebel Ali | City | 2023-2025 | Wikipedia city pages |
| JNPT | **District**, Census of India 2011 | 2011 | Census of India 2011 |

### 6.2 Shared-area rule

Where one administrative area hosts more than one node, the area's population is
split, so that nothing is counted twice:

* **Dubai** (3,944,751; 2025): split **equally** between Dubai Al Quoz and Dubai
  Industrial City (1,972,375.5 each; no published split).
* **San Bernardino County** (2,181,654): divided by **three** among Ontario,
  San Bernardino and Barstow (727,218 each).
* **Pune district** (9,429,408): divided by **two** between Chakan-Talegaon and Pune
  (4,714,704 each).
* **Suzhou** is the prefecture **excluding Kunshan** (12,748,262 - 2,092,496 =
  10,655,766), because Kunshan is its own node.
* **Yiwu** uses the whole Jinhua prefecture (7,050,683; Yiwu alone is 1,859,390), and
  **Ningbo** the whole sub-provincial administrative area (9,404,283).
* Hangzhou, Huzhou and Jiaxing appear in both the Shanghai and Ningbo corridors with
  the same populations.

These rules are crude. Mixed population bases (a whole county for City of Industry,
10,014,009; cities elsewhere) and capital regions give large weights to a few nodes: City
of Industry 0.450 of San Pedro Bay, Brussels 0.373 of Antwerp, Cologne 0.305
and Duisburg 0.302. Weights are **the least defensible input in this file**; the
split-robustness ensemble below exists for that reason. Directional imbalance
(`exp_share`) is a separate assumed input (Section 4).

### 6.3 Across carriers: seeded Dirichlet draws

* A corridor has **3 carriers** at default (`n_carriers = 3`). Market shares are drawn
  once from a Dirichlet distribution with concentration `SHARE_DIRICHLET = 6.0` and a
  fixed seed, **20260909**. Each node's volume is split among the carriers by a
  per-node Dirichlet draw with concentration max(0.25, 8.0 x (1 - `heterogeneity`)); at
  the default `heterogeneity = 0.55` that is 3.6. Heterogeneity zero makes the
  carriers identical and the cooperative game degenerate; the paper reports the
  collaboration gain across the range.
* The collaboration experiment's ten seeds are 20260909, 11, 202, 3003, 40404, 5, 66, 777, 8888
  and 99 (`collaboration_seeds`, run on the lead corridor).
* These are the only stochastic elements of the instance and they are seeded.

### 6.4 Robustness ensemble (`split_ensemble`)

The baseline node split is the population rule. Each of **30 draws per corridor**
(seed 7; `concentration = 4.0`) replaces it with a Dirichlet sample whose parameter
for node n is `4.0 x K x w0_n` (K is the number of demand nodes: 7 for Rotterdam,
8 elsewhere), passed to `build_instance` as `node_weights` (which replaces the
population split and is re-normalised). Each draw re-solves the first-best design (F4)
and the all-diesel corridor (300 s limit at most) and records the emissions change,
social saving, load-weighted grid factor, traction and plan effects, number of
electrified arcs and share of electric truck movements. The aim is that no verdict
depends on the population rule.

---

## 7. Haulage costs

The non-fuel road-haulage cost per truck-kilometre (`wage_usd_km`; column `wage_source`
in `energy_regimes.csv`) is **published for eight corridors** (via four published
sources) and **calibrated for two** (India and the UAE):

| Regime (corridors) | USD/km | Basis | Source and arithmetic |
|---|---|---|---|
| Netherlands (Rotterdam) | 1.204 | **Published** (2024) | CNR (Comite National Routier), *Le transport routier de marchandises neerlandais - 2024*: 40 t articulated truck, international long haul, total EUR 1.60/km; non-fuel excluding overhead EUR 1.1127/km, i.e. the CNR total excluding overhead (EUR 1.43/km) minus the fuel line (EUR 0.31/km), x 1.0820 USD/EUR (2024 Federal Reserve average) |
| Belgium (Antwerp) | 0.993 | **Published** (2021 money, not inflated) | CNR, *Le transport routier de marchandises belge - 2021*: 40 t articulated truck, total EUR 1.26/km; non-fuel excluding overhead EUR 0.8393/km x 1.1830 USD/EUR (2021 average) |
| China-East, North, South (Shanghai, Ningbo, Qingdao, Tianjin, Shenzhen) | 0.641 | **Published** shares of a published rate (2024); one value for all three | CFLP (China Federation of Logistics and Purchasing), *2025 China Road Freight Development Report* (2024 data): 5+ axle trucks CNY 6.78 per vehicle-km; cost shares fuel 32 %, tolls 29 %, driver 22 %, depreciation 10 %, maintenance 5 %, tyres 1 %, insurance 1 %; non-fuel = 68 % x 6.78 = CNY 4.61/km at 7.1957 CNY/USD (2024 Federal Reserve average). The market rate is treated as a cost proxy; tolls (about CNY 1.97/km) are included |
| USA-California (San Pedro Bay) | 1.105 | **Published** (2024) | ATRI, *An Analysis of the Operational Costs of Trucking: 2025 Update*: non-fuel marginal cost USD 1.779 per mile = USD 1.105 per km (driver wages and benefits, truck payments, repair, insurance, permits, tyres, tolls) |
| UAE (Jebel Ali) | 0.50 | **Calibrated assumption** | No published per-kilometre benchmark excluding fuel was located; set relative to national truck-driver wage levels |
| India (JNPT) | 0.32 | **Calibrated** | National road-freight cost benchmarks (driver, vehicle capital, maintenance, insurance, tolls, overhead), treated as a calibrated parameter. The NITI Aayog and RMI figure of INR 34/km (Delhi-Mumbai diesel heavy trucks) contains no component breakdown and is not used |

Haulage cost is not the property of any power system and varies more than threefold
across regimes; the regime matrix therefore also reports a grid-only swap
(`grid_country`) that holds haulage and prices fixed.

**Proposition (haulage neutrality).** The non-fuel haulage cost enters the per-kilometre
cost of the diesel and the electric truck identically, so it cannot change which
traction a truck-kilometre uses; it can change only the **plan** (routes, empty
repositioning, unmet demand). **Traction choice is therefore independent of the
haulage cost**, and the calibrated values for India and the UAE cannot change a
traction conclusion. `haulage_neutrality` (`src/experiments.py`) checks this
numerically: for every corridor it re-solves the first best (F4) and the all-diesel
corridor at 0.5 x, 1.0 x and 2.0 x the base haulage cost (600 s limit) and records
the emissions change, load-weighted grid factor, number of electrified arcs, share of
electric truck movements and the traction and plan effects.

The haulage sensitivity is relative, not absolute: it halves and doubles each
corridor's own cost. The `wage` row of `parameters.csv` records the lead case
(Rotterdam, 1.204 USD/km, range 0.602-2.408), which is that rule applied to the
Netherlands.

---

## 8. What is published, derived, assumed

### 8.1 Summary

| Quantity | Published | Derived from published figures | Assumed or calibrated |
|---|---|---|---|
| Port throughput (TEU) | All ten ports (San Pedro Bay = sum of two ports) | -- | -- |
| Transshipment share | Shanghai | -- | the other nine |
| Road share | Rotterdam | JNPT (rail volume), San Pedro Bay (on-dock rail), Shenzhen (2022 shares) | Antwerp, Shanghai, Ningbo, Qingdao, Tianjin, Jebel Ali |
| TEU per truck | -- | -- | all ten |
| Grid average | China x3 (MEE 2023), CAMX (eGRID2023), India (CEA v22.0), Netherlands (CBS 2024) | -- | -- (Belgium, UAE: Ember lifecycle, published but compiled and on a different basis) |
| Grid marginal and cleanest | China x3 (NCSC 2024 edition), India (CEA v22.0) | Netherlands and UAE (derived from published IFI v2.0 CM pairs), Belgium (derived from the published IFI v3.2 CM pair via EIB), Section 1.3; California marginal (EPA non-baseload proxy) | California cleanest = bound 0 (physical bound) |
| Combined margin | India (CEA v22.0); IFI firm CM for NL and UAE (v2.0) and BE (v3.2) | China (equal-weight blend of NCSC OM and BM) | -- |
| Scenario probabilities | -- | solved so that the mean equals the published average | `OUTER_MASS` 0.50 |
| Electricity price | Netherlands, India, Belgium, UAE (GPP); California (EIA) | China (regional tariffs as proxies for grids; North = mean of two provinces) | state multipliers 0.80 / 1.00 / 1.55 |
| Diesel price | all eight regimes (GPP; EIA for California; Goodreturns/PPAC for India) | -- | -- |
| Vehicle energy, diesel consumption, platooning, diesel CO2, SCC | all (Section 3) | grid-side energy 1.36 kWh/km | charger efficiency 0.92, platoon cap 0.75, `c_platoon`, capex rows, grid-stress weight, unmet penalty |
| Node coordinates | all | -- | -- |
| Arc lengths | Venlo-Duisburg 75 km, Ningbo-Yiwu 181 km (routing estimate) | all other arcs: great circle x fitted circuity | circuity factors fitted to one reference route each |
| Node weights | Populations | `demand_weight` = population share, shared areas split | the splits themselves (Dubai half, San Bernardino County third, Pune district half) |
| Export share per node | -- | -- | all |
| Carrier shares and tilts | -- | -- | seeded Dirichlet |
| Haulage cost | Netherlands, Belgium, China, California | -- | UAE, India |
| T&D losses | -- | -- | India 0.17 and Netherlands 0.04 are country-level aggregates; 0.10 placeholder elsewhere |

### 8.2 Known inconsistencies and gaps in the input files

* **Exchange-rate column.** Belgium's `fx_per_usd` = 0.924 does not reproduce its own
  stated prices (EUR 0.233 = USD 0.277 and EUR 1.64 = USD 1.95 both imply about 0.841).
  China's diesel (CNY 6.41 = USD 0.93) implies 6.89 CNY/USD against the 7.19 recorded
  (which does reproduce the electricity tariffs). The USD prices, not the column, are what
  the model reads.
* **Haulage, UAE `wage_source` text.** The UAE row of `energy_regimes.csv` still says
  its haulage cost is "varied 0.20-1.20 USD/km"; the sensitivity analysis now halves and
  doubles each corridor's own cost (Section 7).
* **Chinese margins.** The model now uses the NCSC 2024 edition (OM = weighted mean of
  2020-2022 data). The MEE 2019 edition (OM / BM: East 0.7921 / 0.3870, North
  0.9419 / 0.4819, Southern 0.8042 / 0.2135) is **superseded**; `grid_factor_sources.csv`
  keeps its rows marked "2019 (superseded)", although their notes still carry the
  older phrase "Latest edition of this series found", which no longer holds. The
  research notes' third-party transcription of a 2023 edition (East 0.7703 / 0.2030,
  North 0.9350 / 0.3020, Southern 0.7738 / 0.1981) is not used. India's CEA v21.0 is
  likewise superseded by v22.0 (Section 1.2).
* **IFI rows in `grid_factor_sources.csv`.** The file holds v3.2 combined margins for
  Belgium and China, marks the United States and India v3.2 as not retrieved, and marks
  the Netherlands (418 / 246) and UAE (450 / 333) v3.2 values "NOT USED" because they
  could not be confirmed verbatim; the Netherlands and the UAE now use IFI v2.0 (Section
  1.3). The v2.0 rows' notes still read "Superseded by v3.2", although the Netherlands
  and UAE v2.0 pairs are model inputs (the UAE pair is also repeated as "Used in the
  model"). Its Belgium Ember row refers to "the NL Ember 0.254", whereas the Netherlands
  is a CBS (direct) row. The research notes' Dutch margins (0.521 / 0.108) and the
  earlier 0.520 / 0.111 were derived from the unconfirmed v3.2 pair and are superseded.
* **Belgian average on three bases.** Ember lifecycle 0.1498 (used), the AwAC
  consumption-side figures 0.186 (2023) and 0.190 (2024) reported in the research notes
  and the University of Liege estimate of 127.6 g/kWh for 2024; the choice moves the
  average by up to 25 %.
* **Population vintages differ between `node_populations.csv` and the research notes.**
  Brussels 1,249,597 (2024) against 1,255,834 (2026); Cologne 1,025,523 (31 Dec 2025)
  against 1,024,621 (2024); Venlo 101,988 (2021) against 103,984 (2025); Shenzhen
  17,560,000 (rounded) against 17,494,398; Thane 11,060,148 (undivided district) against
  8,070,032 on post-2014 boundaries, which would change Bhiwandi's weight; and the notes call the
  US counties 2025 estimates where the CSV records the 2020 Census. The CSV is what the
  model reads.
* **Export share.** Every `exp_share` is an assumption; the research notes left
  the new networks at 0.50, while the files carry 0.55 (China), 0.45 (Antwerp), 0.35
  (San Pedro Bay), and node-specific values in Rotterdam, Shanghai, Jebel Ali and JNPT.
* **Coordinate sources** cover only six corridors (Section 4); Shenzhen's reference route
  uses 107.5 km great circle in `ports.csv` against 104.1 km in the research notes.
* **Haulage, Belgium.** The file's EUR 0.8393/km non-fuel excluding overhead differs from the
  research notes' estimate of about EUR 0.95/km (EUR 1.26 total less about EUR 0.31 fuel),
  which was not re-fetched; the Dutch figure excludes overhead whereas the notes' EUR 1.29/km
  includes it.
* **California electricity** 26.36 cents/kWh rests on secondary relays of EIA data.
* **Ensemble documentation.** The `split_ensemble` docstring says the draw is
  Dirichlet(concentration x w0); the code uses concentration x K x w0 (Section 6.4).

### 8.3 Known limitations

* **Netherlands diesel is a retail pump price including VAT** (GPP, EUR 1.82/L = USD
  2.17/L). Hauliers reclaim VAT, so this overstates the diesel cost of the lead
  corridor. It affects costs only, not the emission-neutral grid threshold, which
  depends on fuel consumption and emission factors, not prices.
* **The `fx_per_usd` column is documentation only.** It is read by `src/data_io.py`
  but not used in any computation; the model reads the USD prices directly.
* **Years are mixed.** JNPT throughput is a fiscal year (FY2024-25, April-March), the
  Belgian haulage cost is in 2021 money (not inflated), and the social cost of carbon is
  in 2020 US dollars (not rebased), while most other prices and costs are 2024-26
  figures.

---

## 9. Global atlas data (`atlas_ports.csv`)

The atlas places the grid of each of the **world's 50 busiest container ports** against the
emission-neutral threshold (`global_atlas`, `src/experiments.py`; output
`global_atlas.csv`).

* **Ports and throughput.** Ranked by 2024 container throughput (`teu_2024_thousand`;
  Shanghai 51,506 thousand TEU to Balboa 4,014 thousand), from the Wikipedia *List of busiest
  container ports* (table citing the Lloyd's List Top 100 and the World Shipping
  Council), extracted 7 Oct 2026 with a summarising fetch tool and to be spot-checked
  against the page. The ports are in 15 Chinese cases, five US, three Vietnamese, and
  smaller counts elsewhere.
* **Grid factor.** National **Ember lifecycle** gCO2e/kWh via Our World in Data
  (`carbon-intensity-electricity`, updated 2026-06-30). The 2025 value is used for 49
  ports; Hong Kong (559 g/kWh, 2023) is absent from the Ember series and comes from
  LowCarbonPower, flagged "verify". Six ports (Jebel Ali, Abu Dhabi, Tanjung Priok,
  Tanjung Perak, Colon, Balboa) have a 2025 value identical to 2024 and are likely
  carried forward rather than observed. Examples: China 525.34 (2024: 555.4),
  Singapore 497.09, Rotterdam 253.56, Antwerp-Bruges 149.82, Los Angeles 384.4, Jebel Ali
  467.51, Mundra and JNPT 670.13.
* **China.** Ember gives only a national value (525.34), so every Chinese port carries
  it. Each Chinese port is also tagged with its regional grid, and the **MEE 2023
  official regional averages** (direct CO2, not lifecycle) are used as the second,
  official value: East 0.5500 (Shanghai, Ningbo-Zhoushan, Xiamen, Taicang/Suzhou,
  Lianyungang), North 0.6361 (Qingdao, Tianjin, Rizhao, Yantai), Southern 0.4042
  (Shenzhen, Guangzhou, Beibu Gulf, Dongguan), Northeast 0.5122 (Yingkou, Dalian). The
  official values are **hard-coded in `global_atlas`** (which also lists Central 0.5271
  and Northwest 0.5543, used by no port); only East, North and Southern are also in
  `grid_factor_sources.csv`. The notes column quotes 2023 and 2022 regional values and
  2022 provincial values (for example Shanghai 584.9, Tianjin 704.1 g/kWh), which are
  the 2022 edition and differ from the 2023 provincial values in Section 1.4.
* **Boundaries compared.** Ember lifecycle values are classified against the
  **delivered / well-to-wheel** threshold interval (0.564-1.036 kg/kWh, Section 3);
  the Chinese official direct values against the **busbar / tank-to-wheel** interval
  (0.481-0.848). Each port is reported "below", "inside" or "above" its interval.
* **Relation to the corridors.** The atlas boundaries differ from the model's regime
  table: Rotterdam is 0.254 (Ember) here and 0.200 (CBS) in the model; Los Angeles and
  Long Beach carry the US national 0.384 while the model uses CAMX 0.194; India is 0.670
  here and 0.675 (CEA v22.0) in the model; Belgium and the UAE agree.

---

## 10. Sources, URLs and retrieval dates

Retrieved **7 October 2026** (`accessed` column and research notes) unless stated.

**Traffic (`ports.csv`)**

* Port of Rotterdam, 2025 throughput (14.2 M TEU, 428.4 Mt); hinterland modal split 2022 (road 59 %, barge 30 %, rail 11 %; BALM report as cited by UIRR). URLs not recorded in the files.
* Port of Antwerp-Bruges, 2025 (13.63 M TEU): https://container-news.com/antwerp-bruges-holds-container-volumes-steady-in-2025 ; and https://www.ajot.com/news/port-of-antwerp-bruges-ends-2025-with-resilience-in-a-turbulent-trading-climate . Container modal split, 2016 (road 54.92 %, barge 38.14 %, rail 6.93 %), EC state-aid decision: https://ec.europa.eu/competition/state_aid/cases/275891/275891_2026100_166_2.pdf
* Port of Shanghai 2025 (55.06 M TEU, transshipment 7.911 M TEU): https://container-news.com/port-of-shanghai-handles-55-06-million-teus-in-2025
* Ningbo-Zhoushan 2025 (43.87 M TEU): https://container-news.com/global-container-port-throughput-exceeds-1-billion-teu-in-2025/ ; sea-rail above 2 M TEU: https://ningbo.chinadaily.com.cn/2025-12/26/c_1150882.htm
* Qingdao 2025 (32.89 M TEU): the same Container News article; sea-rail 2.625 M TEU January-November: https://stock.10jqka.com.cn/20251208/c673032090.shtml
* Tianjin 2025 (24.03 M TEU): https://news.ifeng.com/c/8s9pjQt19aW ; 2025 sea-rail forecast: https://cs.com.cn/xwzx/hg/202506/t20250613_6495939.html ; 2024 figure (23.29 M TEU) from Lloyd's List via Wikipedia, as recorded in `ports.csv`; Xinhua report (4 Jan 2026): https://www.news.cn/fortune/20260104/719560a4bb08401bb1fd579dfc32b728/c.html
* Shenzhen 2025 (35.41 M TEU): the Container News article above; 2022 sea-rail and combined-port volumes: https://www.sz.gov.cn/en_szgov/news/latest/content/post_10368167.html
* Port of Los Angeles 2025 (10,239,318 TEU): https://container-news.com/port-of-los-angeles-container-throughput-tops-10-2-million-teus-in-2025 ; Port of Long Beach 2025 (9,881,595 TEU): https://container-news.com/port-of-long-beach-moves-nearly-9-9-million-teus-in-2025 ; on-dock rail share: https://portoflosangeles.org/business/supply-chain/rail
* DP World FY2025 (Jebel Ali, 15.55 M TEU): https://www.themaritimestandard.com/?p=31957
* Jawaharlal Nehru Port Authority FY2024-25 (7.3 M TEU, 1,078,315 TEU by rail), via *Maritime Gateway*: https://www.maritimegateway.com/jnpa-handles-record-7-3-million-teus-cargo-in-fy-2024-25/

**Road distances for the circuity reference routes**

* Antwerp-Liege: https://en.wikipedia.org/wiki/European_route_E313
* Shanghai-Nanjing Expressway: https://en.wikipedia.org/wiki/Shanghai%E2%80%93Nanjing_Expressway
* Ningbo-Yiwu: https://www.rome2rio.com/s/Ningbo/Yiwu ; Qingdao-Jinan: https://www.rome2rio.com/s/Qingdao/Jinan ; Tianjin-Beijing: https://www.rome2rio.com/s/Tianjin/Beijing
* Guangshen Expressway: https://en.wikipedia.org/wiki/Guangshen_Expressway
* Mumbai-Pune Expressway: https://en.wikipedia.org/wiki/Mumbai%E2%80%93Pune_Expressway

**Grid emission factors (`energy_regimes.csv`, `grid_factor_sources.csv`, `atlas_ports.csv`)**

* CBS, *Energie- en emissiefactoren elektriciteit, update 2024* (Dec 2025): https://www.cbs.nl/nl-nl/achtergrond/2025/49/energie-en-emissiefactoren-elektriciteit-update-2024
* EIB, *Project Carbon Footprint Methodologies* v11.4 (6 Mar 2026), Table A1.3 (IFI v3.2; Belgium only, the Netherlands and UAE v3.2 values are not used): https://www.eib.org/files/publications/20260011-060326-eib-project-carbon-footprint-methodologies-v11-4-en.pdf
* IFI TWG, *GHG Accounting for Grid Connected Renewable Energy Projects* v02.0 (July 2019, OM/BM weights): https://unfccc.int/sites/default/files/resource/Renewable%20Energy_GHG%20accounting%20approach.pdf ; IFI methodological note: https://unfccc.int/sites/default/files/resource/IFITWG_Methodological_approach_to_common_dataset.pdf ; IFI TWG *Dataset of Default Grid Factors* v.2.0 (Jul 2019; Netherlands and UAE combined margins used in the model, other countries for reference): https://unfccc.int/sites/default/files/resource/Harmonized_Grid_Emission_factor_data_set.pdf
* Ember yearly electricity data via Our World in Data (updated 2026-06-30; Belgium, UAE and the atlas): https://ourworldindata.org/grapher/carbon-intensity-electricity.csv
* MEE and NBS, Announcement 2025 No. 47 (31 Dec 2025), 2023 average factors: https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202512/W020251231726284332528.pdf (summary: https://www.mee.gov.cn/ywdt/zbft/202601/t20260105_1139911.shtml); Announcement 2024 No. 33 (2022 edition): https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202412/t20241226_1099413.html
* NCSC, *2024年减排项目中国区域电网二氧化碳基准线排放因子* (2024 edition; OM = weighted mean of 2020-2022 data), Table 3, retrieved 7 Oct 2026: https://www.ccn.ac.cn/wp-content/uploads/2024%E5%B9%B4%E5%87%8F%E6%8E%92%E9%A1%B9%E7%9B%AE%E4%B8%AD%E5%9B%BD%E5%8C%BA%E5%9F%9F%E7%94%B5%E7%BD%91%E4%BA%8C%E6%B0%A7%E5%8C%96%E7%A2%B3%E5%9F%BA%E5%87%86%E7%BA%BF%E6%8E%92%E6%94%BE%E5%9B%A0%E5%AD%90.pdf
* MEE, 2019 regional grid baseline emission factors (published 29 Dec 2020; **superseded** by the NCSC 2024 edition, not used): https://www.mee.gov.cn/ywgz/ydqhbh/wsqtkz/202012/W020201229610353340851.pdf
* US EPA, eGRID2023 summary tables rev. 2 (Jun 2025): https://www.epa.gov/system/files/documents/2025-06/summary_tables_rev2.pdf
* Central Electricity Authority (India), *CO2 Baseline Database* v22.0 (published August 2026; FY2025-26, Table S), retrieved 7 Oct 2026: https://cea.nic.in/wp-content/uploads/baseline/2026/09/User_Guide__Version_22.0.pdf . v21.0 (FY2024-25; 0.710 / 0.961 / 0.512 / 0.736), retrieved 9 Sep 2026, is superseded and not used.
* Hong Kong (atlas only): https://www.lowcarbonpower.org/region/Hong_Kong_SAR_China
* Atlas port list: https://en.wikipedia.org/wiki/List_of_busiest_container_ports

**Prices and costs**

* GlobalPetrolPrices: https://www.globalpetrolprices.com (Belgium: https://www.globalpetrolprices.com/Belgium/electricity_prices/ and https://www.globalpetrolprices.com/Belgium/diesel_prices/); China regional tariffs from the China Briefing compilation of grid-company tariffs (May 2025).
* US EIA: California commercial electricity (2025; 2024 value in Table 2.10: https://www.eia.gov/electricity/annual/html/epa_02_10.html); California No. 2 diesel retail, annual: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=EMD_EPD2D_PTE_SCA_DPG&f=A
* Goodreturns / PPAC retail diesel, Indian metros, 9 Sep 2026.
* CNR, *Le transport routier de marchandises neerlandais - 2024*: https://www.cnr.fr/index.php/en/download/file/publications/CNR-Le%20transport%20routier%20de%20marchandises%20ne%CC%81erlandais%20-%202024%20.pdf ; Belgium 2021: https://www.cnr.fr/en/?p=11668
* CFLP, *2025 China Road Freight Development Report* (summary): https://logev.com/view.php?id=CE36EE-369F1F-21B338-AAEE1F-2A5CE1AE
* ATRI, *An Analysis of the Operational Costs of Trucking: 2025 Update*: https://truckingresearch.org/2025/07/new-atri-report-shows-trucking-profitability-severly-squeezed-by-high-costs-low-rates/

**Populations and coordinates**

* citypopulation.de (Chinese provinces, 2020 census): https://www.citypopulation.de/en/china/admin/32__jiangsu , https://www.citypopulation.de/en/china/admin/33__zhejiang , https://www.citypopulation.de/en/china/admin/37__shandong , https://www.citypopulation.de/en/china/admin/13__hebei
* Wikipedia pages cited per row in `node_populations.csv` and `node_coordinate_sources.csv`; US Census Bureau QuickFacts (2020 county populations); Census of India 2011 (district populations).

**Vehicle and policy (`parameters.csv`, retrieved 9-10 Sep 2026)**

* Le Corguille, Hacker and Dolinga (2025), *Real-world data analysis of battery electric trucks operating in Germany*, EVS38.
* EcoTransIT World Methodology Update 2024; ICCT heavy-duty fleet data; UK DESNZ/DEFRA conversion factors.
* NACFE, *Confidence Report: Two-Truck Platooning*.
* US EPA (2023), *Report on the Social Cost of Greenhouse Gases*, Table ES.1.
