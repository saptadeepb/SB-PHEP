"""
experiments.py
==============
The computational study.  Every number the paper reports is produced here and
written to ``outputs/tables`` as a CSV, so that each table and figure in the
manuscript can be traced back to the file that generated it.

The study is designed around the two questions that decide whether any of it is
worth reporting:

*is the design space large enough that an exact method is needed?* --
:func:`scalability` grows the leader's design space by many orders of magnitude
(the count itself is in :func:`scale.design_space_log10`) while comparing the
proposed strong-duality reformulation against the classical KKT/big-M one and
against explicit enumeration, and reports where each method stops being usable.

*does anything here generalise beyond one national network?* --
:func:`cross_country` runs the full model on four real port-hinterland corridors
in four countries, and :func:`regime_matrix` then crosses every corridor with
every country's energy regime, which separates what is a property of the
*network* from what is a property of the *grid*.
"""
from __future__ import annotations

import csv
import math
import os
import time
from dataclasses import replace
from typing import Dict, List, Optional, Sequence

from . import cooperative_game as CG
from . import models as M
from . import scale as SC
from .instance import DEMAND_LEVELS, Instance, build_instance

TAB = "outputs/tables"


def _write(name: str, header: Sequence[str], rows: Sequence[Sequence]) -> str:
    os.makedirs(TAB, exist_ok=True)
    path = os.path.join(TAB, name)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(list(header))
        for r in rows:
            w.writerow(list(r))
    return path


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# =========================================================================== #
#  1. instrument families: the price of restricting the corridor charge        #
# =========================================================================== #
def instrument_comparison(inst: Instance, families=("F0", "F1", "F2", "F3", "F4"),
                          time_limit: float = 900.0, tag: str = "") -> dict:
    """First-best against each instrument family.

    The *coordination gap* of a family is how much expected social cost it
    leaves on the table relative to the centralized first best.  Theorem 2 says
    the gap of ``F4`` is exactly zero; the others are bounded away from it in
    general, and this experiment measures by how much.
    """
    _log(f"instrument comparison {inst.name}{tag}")
    cen = M.centralized(inst, time_limit=time_limit)
    rows = [["centralized (first best)", cen["obj"], 0.0, 0.0, cen["exp_emis"],
             cen["exp_grid"], cen["n_electrified"], sum(cen["bays"].values()),
             "", "", cen["runtime"], cen.get("mip_gap"), cen.get("status")]]
    res = {"centralized": cen}
    for fam in families:
        r = M.bilevel_sd(inst, fam, time_limit=time_limit)
        res[fam] = r
        if r.get("obj") is None:
            rows.append([fam, "", "", "", "", "", "", "", "", "", r["runtime"],
                         r.get("mip_gap"), r.get("status")])
            continue
        gap = r["obj"] - cen["obj"]
        #  The two models are solved independently, so a first-best that is a
        #  few parts in 10^8 above a restricted family's optimum is solver
        #  tolerance, not an economic result.  Clamp it rather than report a
        #  negative coordination gap, which is impossible by construction.
        if abs(gap) <= 1e-7 * max(1.0, abs(cen["obj"])):
            gap = 0.0
        rows.append([fam, r["obj"], gap, 100.0 * gap / cen["obj"], r["exp_emis"],
                     r["exp_grid"], r["n_electrified"], sum(r["bays"].values()),
                     _fmt(r["theta"]), _fmt(r["sigma"]), r["runtime"],
                     r.get("mip_gap"), r.get("status")])
    _write(f"instruments_{inst.name}{tag}.csv",
           ["model", "exp_social_cost_usd", "coordination_gap_usd", "gap_pct",
            "exp_emissions_kgco2", "exp_grid_kwh", "n_electrified", "n_bays",
            "theta", "sigma", "runtime_s", "certified_mip_gap", "status"], rows)
    return res


def _load_pars():
    from . import data_io as D
    return D.load_parameters()


def _fmt(d) -> str:
    if not d:
        return ""
    return ";".join(f"{k}={v:g}" for k, v in sorted(d.items()))


# =========================================================================== #
#  2. value of the stochastic solution and of perfect information              #
# =========================================================================== #
def _mean_value_instance(inst: Instance) -> Instance:
    price = {"MV": sum(inst.prob[s] * inst.price[s] for s in inst.S)}
    ef = {"MV": sum(inst.prob[s] * inst.ef[s] for s in inst.S)}
    gav = {"MV": sum(inst.prob[s] * inst.Gavail[s] for s in inst.S)}
    DI = {(c, n, "MV"): sum(inst.prob[s] * inst.DI[(c, n, s)] for s in inst.S)
          for c in inst.C for n in inst.Dn}
    DE = {(c, n, "MV"): sum(inst.prob[s] * inst.DE[(c, n, s)] for s in inst.S)
          for c in inst.C for n in inst.Dn}
    return replace(inst, S=["MV"], prob={"MV": 1.0}, price=price, ef=ef,
                   Gavail=gav, DI=DI, DE=DE)


def _single_scenario(inst: Instance, s: str) -> Instance:
    return replace(inst, S=[s], prob={s: 1.0},
                   price={s: inst.price[s]}, ef={s: inst.ef[s]},
                   Gavail={s: inst.Gavail[s]},
                   DI={(c, n, s): inst.DI[(c, n, s)] for c in inst.C for n in inst.Dn},
                   DE={(c, n, s): inst.DE[(c, n, s)] for c in inst.C for n in inst.Dn})


def stochastic_value(inst: Instance, family: str = "F4",
                     time_limit: float = 900.0) -> dict:
    """VSS and EVPI at the leader's here-and-now level."""
    _log(f"stochastic value {inst.name} ({family})")
    rp = M.bilevel_sd(inst, family, time_limit=time_limit)
    RP = rp["obj"]

    ev = _mean_value_instance(inst)
    evs = M.bilevel_sd(ev, family if family != "F4" else "F3", time_limit=time_limit)
    eev = M.bilevel_sd(inst, family, fix_y=evs["y"], fix_bays=evs["bays"],
                       time_limit=time_limit)
    EEV = eev["obj"]

    WS, ws_rows = 0.0, []
    for s in inst.S:
        si = _single_scenario(inst, s)
        r = M.bilevel_sd(si, family if family != "F4" else "F3", time_limit=time_limit)
        WS += inst.prob[s] * r["obj"]
        ws_rows.append([s, inst.prob[s], r["obj"], r["n_electrified"]])

    out = {"RP": RP, "EEV": EEV, "WS": WS, "VSS": EEV - RP, "EVPI": RP - WS,
           "ev_policy": {"y": evs["y"], "bays": evs["bays"]}}
    _write(f"stochastic_value_{inst.name}.csv", ["quantity", "value_usd", "pct_of_RP"],
           [["WS (wait and see)", WS, 100 * WS / RP],
            ["RP (stochastic here-and-now)", RP, 100.0],
            ["EEV (expected result of the mean-value plan)", EEV, 100 * EEV / RP],
            ["VSS = EEV - RP", EEV - RP, 100 * (EEV - RP) / RP],
            ["EVPI = RP - WS", RP - WS, 100 * (RP - WS) / RP]])
    _write(f"wait_and_see_{inst.name}.csv",
           ["scenario", "probability", "objective_usd", "n_electrified"], ws_rows)
    return out


# =========================================================================== #
#  3. cost-emissions frontier under each instrument family                     #
# =========================================================================== #
def min_emissions_under(inst: Instance, family: Optional[str],
                        time_limit: float = 600.0, mip_gap: float = 1e-4) -> dict:
    """Least expected emissions the authority can *induce* while serving all demand.

    With ``family=None`` this is the social planner's minimum, which no
    instrument can beat.  With a family it is that family's **reach**: the
    tightest emission target the authority can hit with that instrument at any
    level, because the carriers must be willing to deliver it.

    Solving this directly replaces probing a sequence of emission caps and
    checking which come back infeasible.  Probing is both slower and unsound: a
    branch-and-bound run that stops on its time limit without an incumbent has
    not proved anything, and reporting it as "unattainable" would overstate the
    result.

    Two numbers are returned and they carry different claims, which matters when
    the solve stops on its time limit:

    ``emis``  the incumbent.  Every emission target at or above it is *attainable*,
              certified by the solution that achieved it.
    ``emis_lb`` the branch-and-bound lower bound.  No target *below* it is
              attainable by this family, certified by the search tree.

    Only when the two meet is the reach known exactly.  Reported separately, each
    supports exactly the direction it proves, so a claim that an authority cannot
    push emissions below some level rests on ``emis_lb`` and never on a
    time-limited incumbent.
    """
    import pyomo.environ as pyo
    if family is None:
        m = pyo.ConcreteModel()
        M._leader_block(m, inst, "F0")
        lps = M._follower_block(m, inst, "F0")
        M._primal_feasibility(m, inst, lps)
    else:
        return _min_emissions_bilevel(inst, family, time_limit, mip_gap)
    _force_full_service(m, inst, lps)
    total, op, em, gr = M._social_objective(m, inst, lps)
    m.OBJ = pyo.Objective(expr=em, sense=pyo.minimize)
    t0 = time.time()
    res, tc, ok = M._solve(m, time_limit=time_limit, mip_gap=mip_gap)
    if not ok:
        return {"status": tc, "emis": None, "emis_lb": _obj_bound(res),
                "runtime": time.time() - t0}
    return {"status": tc, "emis": pyo.value(em), "emis_lb": _obj_bound(res),
            "cost": pyo.value(total),
            "certified": M._certified(tc), "mip_gap": M._gap(res),
            "runtime": time.time() - t0}


def _obj_bound(res) -> Optional[float]:
    """The branch-and-bound lower bound on a minimisation, or ``None``.

    This is the half of a time-limited solve that proves a *negative*: nothing
    below it is attainable.  The incumbent proves the positive.
    """
    try:
        b = res.best_objective_bound
        return float(b) if b is not None else None
    except Exception:
        return None


def _force_full_service(m, inst: Instance, lps) -> None:
    import pyomo.environ as pyo
    m.serve = pyo.ConstraintList()
    for s in inst.S:
        ix = lps[s].index
        for c in inst.C:
            for n in inst.Dn:
                m.serve.add(m.x[s, ix[("uI", c, n)]] == 0)
                m.serve.add(m.x[s, ix[("uE", c, n)]] == 0)


def _min_emissions_bilevel(inst: Instance, family: str, time_limit: float,
                           mip_gap: float) -> dict:
    """The same minimisation, but with the followers' optimality imposed."""
    import pyomo.environ as pyo
    from .bounds import dual_bounds_for

    m = pyo.ConcreteModel()
    M._leader_block(m, inst, family)
    lps = M._follower_block(m, inst, family)
    M._primal_feasibility(m, inst, lps)
    db = dual_bounds_for(inst, family)
    M._dual_block_sd(m, inst, lps, db)
    _force_full_service(m, inst, lps)
    total, op, em, gr = M._social_objective(m, inst, lps)
    m.OBJ = pyo.Objective(expr=em, sense=pyo.minimize)
    t0 = time.time()
    res, tc, ok = M._solve(m, time_limit=time_limit, mip_gap=mip_gap)
    if not ok:
        return {"status": tc, "emis": None, "emis_lb": _obj_bound(res),
                "runtime": time.time() - t0}
    return {"status": tc, "emis": pyo.value(em), "emis_lb": _obj_bound(res),
            "cost": pyo.value(total),
            "certified": M._certified(tc), "mip_gap": M._gap(res),
            "runtime": time.time() - t0,
            "theta": {k: v for k, v in M._extract(m, inst, lps, total, op, em, gr,
                                                  family)["theta"].items()},
            "n_electrified": M._extract(m, inst, lps, total, op, em, gr,
                                        family)["n_electrified"]}


def emissions_frontier(inst: Instance, families=("F0", "F2", "F4"), n_points: int = 5,
                       time_limit: float = 300.0, mip_gap: float = 1e-3) -> dict:
    """Exact epsilon-constraint frontier, computed separately for each family.

    Two things are reported. The *reach* of a family is the tightest emission
    target it can induce, obtained from :func:`min_emissions_under`, which returns
    both the attainable level (its incumbent) and a proved floor below which no
    cap is attainable (its branch-and-bound bound). The *frontier* is then traced
    from the attainable level upwards, so every point solved is feasible and no
    claim rests on an unproved infeasibility.
    """
    _log(f"emissions frontier {inst.name}")
    cen = M.centralized(inst, time_limit=time_limit)
    e_hi = cen["exp_emis"]
    planner = min_emissions_under(inst, None, time_limit=time_limit, mip_gap=mip_gap)
    _log(f"   planner reach: {planner.get('emis')} ({planner.get('status')})")

    reach, rows, out = {}, [], {}
    for fam in families:
        r = min_emissions_under(inst, fam, time_limit=max(time_limit, 600.0),
                                mip_gap=mip_gap)
        reach[fam] = r
        _log(f"   {fam} reach: {r.get('emis')} (floor {r.get('emis_lb')}, "
             f"{r.get('status')}, {r.get('runtime', 0):.0f}s)")

    for fam in families:
        lo = reach[fam].get("emis")
        if lo is None:
            continue
        pts = []
        for i in range(n_points):
            frac = i / (n_points - 1)
            eps = lo + frac * (e_hi - lo)
            rr = M.bilevel_sd(inst, fam, eps_emis=eps, time_limit=time_limit,
                              mip_gap=mip_gap)
            feas = rr.get("obj") is not None
            pts.append({"eps": eps, "feasible": feas, "cost": rr.get("obj"),
                        "emis": rr.get("exp_emis"), "grid": rr.get("exp_grid"),
                        "n_elec": rr.get("n_electrified")})
            rows.append([fam, round(eps, 2), feas, rr.get("obj"), rr.get("exp_emis"),
                         rr.get("exp_grid"), rr.get("n_electrified"),
                         _fmt(rr.get("theta") or {}), _fmt(rr.get("sigma") or {}),
                         rr.get("mip_gap"), rr.get("status"),
                         round(rr.get("runtime", 0), 1)])
            _log(f"   {fam} eps={eps:,.0f} -> {rr.get('status')} "
                 f"{rr.get('obj') if feas else 'no solution'} "
                 f"({rr.get('runtime', 0):.0f}s)")
        out[fam] = pts
    _write(f"frontier_{inst.name}.csv",
           ["family", "eps_emissions", "feasible", "exp_cost_usd", "exp_emissions_kgco2",
            "exp_grid_kwh", "n_electrified", "theta", "sigma", "certified_mip_gap",
            "status", "runtime_s"], rows)
    _write(f"reach_{inst.name}.csv",
           ["family", "min_attainable_emissions_kgco2", "proved_floor_kgco2",
            "cost_at_that_point_usd", "status", "certified_mip_gap", "runtime_s"],
           [["social planner (no incentive constraint)", planner.get("emis"),
             planner.get("emis_lb"),
             planner.get("cost"), planner.get("status"), planner.get("mip_gap"),
             round(planner.get("runtime", 0), 1)]]
           + [[fam, reach[fam].get("emis"), reach[fam].get("emis_lb"),
               reach[fam].get("cost"),
               reach[fam].get("status"), reach[fam].get("mip_gap"),
               round(reach[fam].get("runtime", 0), 1)] for fam in families])
    out["_anchor"] = {"e_hi": e_hi, "c_lo": cen["obj"],
                      "planner_reach": planner.get("emis"),
                      "reach": {k: v.get("emis") for k, v in reach.items()}}
    return out


# =========================================================================== #
#  4. the grid-carbon reversal, in closed form and across countries            #
# =========================================================================== #
def neutral_threshold_interval(inst) -> tuple:
    """The emission-neutral grid intensity and its range over the vehicle data.

    ``ef_neutral = f_diesel * ef_diesel / e_elec`` depends only on the two
    drivetrains.  Both inputs are measured with uncertainty, so the paper reports
    the interval this induces rather than a point, and asks of each published
    grid factor whether it lies above, below or inside it.
    """
    from . import data_io as D
    p = D.load_parameters()
    #  epsilon is metered GRID energy, so the range must combine both ends of the
    #  battery-side consumption range with both ends of the charging-efficiency
    #  range.  Using the battery figure gives a threshold the model does not use and
    #  an interval narrower than the evidence supports.
    eta = p["charger_efficiency"]
    e_lo = p["e_elec"]["low"] / eta["high"]
    e_hi = p["e_elec"]["high"] / eta["low"]
    lo = p["f_diesel"]["low"] * p["ef_diesel_ttw"]["low"] / e_hi
    hi = p["f_diesel"]["high"] * p["ef_diesel_ttw"]["high"] / e_lo
    mid = inst.f_diesel * inst.ef_diesel / inst.e_elec
    return mid, lo, hi


def reversal_analysis(networks=("vizag", "sanantonio", "manzanillo", "rotterdam")) -> dict:
    """Where each grid sits relative to the two thresholds of Section 5.

    ``ef_neutral``  the grid carbon intensity at which one electric truck-km
                    emits exactly as much as one diesel truck-km.  It depends
                    only on vehicle technology, not on prices or policy:
                        ef_neutral = f_diesel * ef_diesel / e_elec.
    ``ef_social``   the grid carbon intensity at which electrification stops
                    lowering *weighted social cost*; it also depends on the
                    energy prices and the carbon price.
    """
    _log("reversal analysis")
    rows = []
    out = {}
    for nm in networks:
        inst = build_instance(nm)
        ef_neutral, ef_lo, ef_hi = neutral_threshold_interval(inst)
        for s in inst.S:
            ef_social = M.break_even_ef(inst, s)
            em_e = inst.e_elec * inst.ef[s]
            em_d = inst.f_diesel * inst.ef_diesel
            #  carbon price at which the social ranking flips in this state
            denom = inst.e_elec * inst.ef[s] - inst.f_diesel * inst.ef_diesel
            num = inst.f_diesel * inst.p_diesel - inst.e_elec * (inst.price[s] + inst.w_grid)
            w_flip = (num / denom) if denom > 1e-12 else float("inf")
            verdict = ("electric, robustly" if inst.ef[s] < ef_lo else
                       "diesel, robustly" if inst.ef[s] > ef_hi else
                       "undetermined by the data")
            rows.append([nm, inst.country, s, inst.ef[s], round(ef_neutral, 4),
                         round(ef_lo, 4), round(ef_hi, 4),
                         round(ef_social, 4), round(em_e, 4), round(em_d, 4),
                         "electric" if em_e < em_d else "diesel", verdict,
                         "electric" if inst.ef[s] < ef_social else "diesel",
                         round(w_flip, 4) if math.isfinite(w_flip) else ""])
        out[nm] = {"ef_neutral": ef_neutral, "ef_neutral_lo": ef_lo,
                   "ef_neutral_hi": ef_hi,
                   "ef_social": {s: M.break_even_ef(inst, s) for s in inst.S},
                   "ef": dict(inst.ef)}
    _write("reversal_thresholds.csv",
           ["network", "country", "scenario", "ef_grid_kgco2_kwh", "ef_neutral",
            "ef_neutral_low", "ef_neutral_high", "ef_social_breakeven",
            "elec_kgco2_per_km", "diesel_kgco2_per_km", "cleaner_option",
            "robustness_of_sign", "socially_cheaper_option",
            "carbon_price_flip_usd_kg"], rows)

    #  Every *published* factor against the interval, including ones the scenario
    #  tree does not use.  India's CDM combined margin is the case in point: it is
    #  the convention's own factor for assessing a programme that adds new load, and
    #  omitting it made the Indian result look like a two-way choice.
    from . import data_io as D
    reg = D.load_energy_regimes()
    inst0 = build_instance(networks[0])
    mid, lo, hi = neutral_threshold_interval(inst0)
    frows = []
    for c, v in reg.items():
        for key, lab in (("ef_clean", "build margin / cleanest state"),
                         ("ef_avg", "published weighted average"),
                         ("ef_combined", "CDM combined margin"),
                         ("ef_marginal", "operating margin / marginal state")):
            x = v.get(key)
            if x is None:
                continue
            frows.append([c, lab, x, round(mid, 4), round(lo, 4), round(hi, 4),
                          "above" if x > hi else ("below" if x < lo else "inside"),
                          key in ("ef_avg",) or (c == "India" and key != "ef_clean"),
                          key in ("ef_clean", "ef_avg", "ef_marginal")])
    #  The same question under the ALTERNATIVE accounting boundary, because the
    #  paper's strongest empirical claim is a sign relative to this threshold and the
    #  boundary moves both sides of it by different proportions.  Reporting only that
    #  the country ordering survives would not address the claim that is made.
    pars = _load_pars()
    losses = {"India": 0.17, "Chile": 0.05, "Mexico": 0.12, "Netherlands": 0.04}
    ef_d_wtw = pars["ef_diesel_wtw"]["value"]
    eta = pars["charger_efficiency"]
    e_lo_ = pars["e_elec"]["low"] / eta["high"]
    e_hi_ = pars["e_elec"]["high"] / eta["low"]
    mid_w = inst0.f_diesel * ef_d_wtw / inst0.e_elec
    lo_w = pars["f_diesel"]["low"] * ef_d_wtw / e_hi_
    hi_w = pars["f_diesel"]["high"] * ef_d_wtw / e_lo_
    for c, v in reg.items():
        L = losses.get(c, 0.10)
        for key, lab in (("ef_clean", "build margin / cleanest state"),
                         ("ef_avg", "published weighted average"),
                         ("ef_combined", "CDM combined margin"),
                         ("ef_marginal", "operating margin / marginal state")):
            x = v.get(key)
            if x is None:
                continue
            xd = x / (1.0 - L)          # delivered rather than busbar
            frows.append([c, lab + " (delivered vs well-to-wheel)", round(xd, 4),
                          round(mid_w, 4), round(lo_w, 4), round(hi_w, 4),
                          "above" if xd > hi_w else ("below" if xd < lo_w else "inside"),
                          True, False])
    _write("threshold_positions.csv",
           ["country", "factor", "ef_kgco2_kwh", "ef_neutral", "ef_neutral_low",
            "ef_neutral_high", "position_vs_interval", "published_by_the_country",
            "used_as_a_scenario_state"], frows)
    _log(f"   threshold interval [{lo:.4f}, {hi:.4f}] around {mid:.4f}; under the "
         f"alternative boundary [{lo_w:.4f}, {hi_w:.4f}] around {mid_w:.4f}")
    return out


# =========================================================================== #
#  5. cross-country study and the network x regime matrix                      #
# =========================================================================== #
def cross_country(networks=("vizag", "sanantonio", "manzanillo", "rotterdam"),
                  family: str = "F4", time_limit: float = 900.0,
                  all_families=("F0", "F1", "F2", "F3", "F4")) -> dict:
    """Every corridor under its own national regime, with every instrument family.

    Solving only F0 and F4 away from the focal corridor would leave the statement
    that the platoon-waiver toll is worth nothing "on our instances" displayed for
    one instance out of four.  All five families are therefore solved on all four
    corridors, and the per-family table is written alongside the headline one so the
    claim can be checked where it is made.
    """
    _log("cross-country study")
    rows, fam_rows, out = [], [], {}
    for nm in networks:
        inst = build_instance(nm)
        cen = M.centralized(inst, time_limit=time_limit)
        res = {}
        for fam in all_families:
            res[fam] = M.bilevel_sd(inst, fam, time_limit=time_limit)
            g = (res[fam]["obj"] - cen["obj"]) if res[fam].get("obj") else None
            if g is not None and abs(g) <= 1e-7 * max(1.0, abs(cen["obj"])):
                g = 0.0
            fam_rows.append([nm, inst.port, inst.country, fam, cen["obj"],
                             res[fam].get("obj"), g,
                             (100.0 * g / cen["obj"]) if g is not None else None,
                             res[fam].get("exp_emis"), res[fam].get("n_electrified"),
                             _fmt(res[fam].get("theta") or {}),
                             _fmt(res[fam].get("sigma") or {}),
                             res[fam].get("mip_gap"), res[fam].get("status"), None])
            _log(f"   {nm} {fam}: {res[fam].get('obj')} gap {g} "
                 f"({res[fam].get('status')})")
        #  The families are nested -- F0 is F4 at a zero charge, F3 is F4 state-blind --
        #  so gap(F4) <= gap(F3) <= gap(F0) must hold.  A time-limited incumbent can
        #  violate that, and a row that does is marked rather than quietly printed.
        tolc = 1e-6 * max(1.0, abs(cen["obj"] or 1.0))
        gap_of = {}
        for fam in all_families:
            gg = (res[fam]["obj"] - cen["obj"]) if res[fam].get("obj") else None
            gap_of[fam] = 0.0 if (gg is not None and abs(gg) <= 1e-7 * max(
                1.0, abs(cen["obj"]))) else gg
        def _nest_ok(fam):
            g_ = gap_of.get(fam)
            if g_ is None:
                return False
            for sup in {"F0": (), "F1": (), "F2": (), "F3": ("F0",),
                        "F4": ("F0", "F3")}.get(fam, ()):
                gs_ = gap_of.get(sup)
                if gs_ is not None and g_ > gs_ + tolc:
                    return False
            return True
        for row in fam_rows[-len(all_families):]:
            row[-1] = _nest_ok(row[3])

        f0, f4 = res["F0"], res[family]
        base = f0["obj"] if f0.get("obj") else float("nan")
        out[nm] = {"centralized": cen, "instance": inst, **res}
        rows.append([nm, inst.port, inst.country, len(inst.E), len(inst.arcs),
                     inst.meta["daily_boxes"], cen["obj"], f0["obj"], f4["obj"],
                     base - f4["obj"], 100.0 * (base - f4["obj"]) / base,
                     cen["n_electrified"], f0["n_electrified"], f4["n_electrified"],
                     cen["exp_emis"], f0["exp_emis"], f4["exp_emis"],
                     100.0 * (f0["exp_emis"] - f4["exp_emis"]) / f0["exp_emis"],
                     inst.meta["expected_ef_kgco2_per_kwh"],
                     inst.meta["published_ef_avg"]])
    _write("cross_country.csv",
           ["network", "port", "country", "n_edges", "n_arcs", "boxes_per_day",
            "cost_first_best", "cost_no_charge", f"cost_{family}",
            "value_of_charge_usd", "value_of_charge_pct",
            "n_elec_first_best", "n_elec_no_charge", f"n_elec_{family}",
            "emis_first_best", "emis_no_charge", f"emis_{family}",
            "emission_cut_pct", "expected_ef_kgco2_per_kwh",
            "published_ef_avg"], rows)
    _write("cross_country_families.csv",
           ["network", "port", "country", "family", "first_best", "cost_usd",
            "coordination_gap_usd", "gap_pct", "exp_emissions_kgco2",
            "n_electrified", "theta", "sigma", "certified_mip_gap", "status",
            "nesting_consistent"],
           fam_rows)
    return out


def regime_matrix(networks=("vizag", "sanantonio", "manzanillo", "rotterdam"),
                  countries=("India", "Chile", "Mexico", "Netherlands"),
                  family: str = "F4", time_limit: float = 900.0) -> dict:
    """Cross every corridor topology with every national regime, twice.

    The question is whether a result belongs to *the Indian grid* or to *the
    Visakhapatnam corridor*.  Answering it needs care about what the column
    dimension actually varies, so the matrix is computed under two swaps:

    ``full``  the whole national regime -- grid carbon factors, electricity price,
              diesel price and the non-fuel haulage cost.  This is the right
              object for "what if this corridor were in that country", but it is
              not a grid experiment: the haulage cost alone ranges more than
              threefold across these four countries.
    ``grid``  the three emission factors only, with every price and cost held at
              the corridor's own country.  This isolates the grid.

    Reporting only the first would licence a conclusion about power systems from a
    design that also moves wages.
    """
    _log("network x regime matrix")
    rows = []
    for swap in ("full", "grid"):
        for nm in networks:
            for ctry in countries:
                inst = (build_instance(nm, country=ctry) if swap == "full"
                        else build_instance(nm, grid_country=ctry))
                r = M.bilevel_sd(inst, family, time_limit=time_limit)
                cen = M.centralized(inst, time_limit=time_limit)
                share_e = sum(r["perS"][s]["electric"] * inst.prob[s] for s in inst.S)
                share_t = sum(r["perS"][s]["trucks"] * inst.prob[s] for s in inst.S)
                rows.append([swap, nm, ctry, r["obj"], cen["obj"],
                             r["n_electrified"], len(inst.E),
                             100.0 * r["n_electrified"] / len(inst.E),
                             100.0 * share_e / share_t if share_t else 0.0,
                             r["exp_emis"], r["exp_grid"],
                             r["exp_emis"] / (inst.H * share_t) if share_t else 0.0,
                             inst.meta["expected_ef_kgco2_per_kwh"], inst.wage,
                             r.get("status")])
                _log(f"   [{swap}] {nm} under {ctry}: "
                     f"{100.0 * share_e / max(share_t, 1e-9):.1f}% electric "
                     f"({r.get('status')})")
    _write("regime_matrix.csv",
           ["swap", "network", "regime_country", "cost_usd", "cost_first_best",
            "n_electrified", "n_electrifiable", "pct_electrified",
            "pct_truck_movements_electric", "exp_emissions_kgco2", "exp_grid_kwh",
            "emissions_per_truck_movement", "expected_ef_kgco2_per_kwh",
            "haulage_cost_usd_per_km", "status"], rows)
    return {"rows": rows}


# =========================================================================== #
#  6. sensitivity analysis                                                     #
# =========================================================================== #
def _rescaled_volume(inst: Instance, road_share_mult: float = 1.0,
                     transship_mult: float = 1.0,
                     teu_factor_mult: float = 1.0) -> Instance:
    """Rescale every demand by a change in the port-level volume shares.

    ``road_share``, ``transshipment_share`` and ``truck_teu_factor`` enter the
    instance only through the daily box count, so a change in any of them is a
    uniform scaling of all demands.  That is exactly the claim ``DATA_SOURCES.md``
    makes about them, and rescaling here is how it is tested rather than asserted.
    """
    rs = inst.meta["road_share"] * road_share_mult
    ts = min(0.95, inst.meta["transshipment_share"] * transship_mult)
    base = (inst.meta["road_share"] * (1.0 - inst.meta["transshipment_share"]))
    new = (min(1.0, rs) * (1.0 - ts)) / teu_factor_mult
    k = new / base if base > 0 else 1.0
    return replace(inst,
                   DI={key: v * k for key, v in inst.DI.items()},
                   DE={key: v * k for key, v in inst.DE.items()})


def sensitivity(inst: Instance, family: str = "F4", time_limit: float = 180.0,
                mip_gap: float = 1e-4) -> dict:
    _log(f"sensitivity {inst.name}")
    rows = []

    def record(param, value, r, extra=""):
        rows.append([param, value, r.get("obj"), r.get("exp_emis"), r.get("exp_grid"),
                     r.get("n_electrified"), sum((r.get("bays") or {}).values()),
                     _fmt(r.get("theta") or {}), _fmt(r.get("sigma") or {}), extra,
                     r.get("mip_gap"), r.get("status")])
        _log(f"   {param}={value}: {r.get('obj')} ({r.get('status')}, "
             f"{r.get('runtime', 0):.0f}s)")

    #  Every range below is the documented low-central-high of data/parameters.csv,
    #  not a hand-picked ladder, so that the sweep cannot stray outside a documented
    #  range for one parameter while never reaching the documented bound for another.
    #  Reading the bands from the file is what makes the coverage claim true.
    pars0 = _load_pars()

    def band(name, extra=()):
        p = pars0[name]
        return sorted({p["low"], p["value"], p["high"], *extra})

    for scc in sorted({0.0, *band("scc"), 0.55, 0.80}):
        i2 = replace(inst, w_emis=scc)
        record("social_cost_of_carbon_usd_per_kg", scc,
               M.bilevel_sd(i2, family, time_limit=time_limit, mip_gap=mip_gap))
    for ps in band("platoon_saving"):
        record("platoon_saving_fraction", ps,
               M.bilevel_sd(replace(inst, psave=ps), family, time_limit=time_limit, mip_gap=mip_gap))
    #  e_elec is swept on the GRID side, which is what the model uses: the battery
    #  figure divided by the charging efficiency, at both ends of both ranges.
    eta = pars0["charger_efficiency"]
    for lab, ee in (("low battery / best charger",
                     pars0["e_elec"]["low"] / eta["high"]),
                    ("central", pars0["e_elec"]["value"] / eta["value"]),
                    ("high battery / worst charger",
                     pars0["e_elec"]["high"] / eta["low"])):
        record("e_truck_kwh_per_km_grid_side", round(ee, 4),
               M.bilevel_sd(replace(inst, e_elec=ee), family,
                            time_limit=time_limit, mip_gap=mip_gap), lab)
    for fd in band("f_diesel"):
        record("diesel_l_per_km", fd,
               M.bilevel_sd(replace(inst, f_diesel=fd), family,
                            time_limit=time_limit, mip_gap=mip_gap))
    for ed in band("ef_diesel_ttw"):
        record("diesel_kgco2_per_l", ed,
               M.bilevel_sd(replace(inst, ef_diesel=ed), family,
                            time_limit=time_limit, mip_gap=mip_gap))
    for wg in (0.5, 1.0, 1.5):
        record("electricity_price_multiplier", wg,
               M.bilevel_sd(replace(inst, price={s_: inst.price[s_] * wg
                                                 for s_ in inst.S}), family,
                            time_limit=time_limit, mip_gap=mip_gap))
    for dm in (0.7, 1.0, 1.4):
        record("diesel_price_multiplier", dm,
               M.bilevel_sd(replace(inst, p_diesel=inst.p_diesel * dm), family,
                            time_limit=time_limit, mip_gap=mip_gap))
    for gw in band("grid_stress_weight"):
        record("grid_stress_weight_usd_per_kwh", gw,
               M.bilevel_sd(replace(inst, w_grid=gw), family,
                            time_limit=time_limit, mip_gap=mip_gap))
    for cb in band("charger_capex"):
        sc_ = cb / pars0["charger_capex"]["value"]
        record("charging_capacity_cost_usd_per_unit", round(inst.module_cost * sc_, 1),
               M.bilevel_sd(replace(inst, module_cost=inst.module_cost * sc_), family,
                            time_limit=time_limit, mip_gap=mip_gap))
    for kf in band("electrify_capex_fixed"):
        record("electrification_fixed_cost_usd", kf,
               M.bilevel_sd(replace(inst, K_fix={e: kf for e in inst.E}), family,
                            time_limit=time_limit, mip_gap=mip_gap))
    for cp in band("c_platoon", extra=(0.5, 8.0)):
        record("platoon_coordination_cost_usd", cp,
               M.bilevel_sd(replace(inst, c_plat=cp), family, time_limit=time_limit, mip_gap=mip_gap))
    for mult in (0.5, 0.75, 1.0, 1.5, 2.0):
        i2 = replace(inst, Gavail={s: inst.Gavail[s] * mult for s in inst.S})
        record("grid_headroom_multiplier", mult,
               M.bilevel_sd(i2, family, time_limit=time_limit, mip_gap=mip_gap))
    for rho in band("platoon_share_cap"):
        record("platoon_share_cap", rho,
               M.bilevel_sd(replace(inst, rho=rho), family, time_limit=time_limit, mip_gap=mip_gap))
    for wg in (0.20, inst.wage, 0.60, 1.20):
        record("haulage_cost_usd_per_km", wg,
               M.bilevel_sd(replace(inst, wage=wg), family, time_limit=time_limit, mip_gap=mip_gap))
    for pen in band("unmet_penalty", extra=(400.0, 2000.0)):
        record("unmet_demand_penalty_usd", pen,
               M.bilevel_sd(replace(inst, PEN=pen), family, time_limit=time_limit, mip_gap=mip_gap))
    base_circ = _load_pars()["circuity"]
    for circ, lab in ((base_circ["low"], "lower bound, straight-line"),
                      (inst.meta["circuity"], "fitted for this corridor"),
                      (base_circ["high"], "upper bound")):
        i2 = build_instance(inst.name, n_carriers=len(inst.C))
        scale = circ / inst.meta["circuity"]
        i2 = replace(i2, dist={a: v * scale for a, v in i2.dist.items()})
        record("circuity_factor", circ, M.bilevel_sd(i2, family, time_limit=time_limit, mip_gap=mip_gap), lab)
    #  volume composition: the three port-level shares that set how many trucks the
    #  corridor carries.  DATA_SOURCES says they scale the corridor rather than
    #  change its composition; this is the experiment that tests the claim.
    for lab, kw in (("road share low", {"road_share_mult": 0.85}),
                    ("road share high", {"road_share_mult": 1.15}),
                    ("transshipment share high", {"transship_mult": 1.5}),
                    ("boxes per TEU low", {"teu_factor_mult": 0.9})):
        i2 = _rescaled_volume(inst, **kw)
        record("volume_composition", lab,
               M.bilevel_sd(i2, family, time_limit=time_limit, mip_gap=mip_gap), lab)
    #  the entitlement rule is swept in the collaboration experiment, where it
    #  actually bites; recorded here so the table is a complete list of what moved
    #  accounting boundary: the base case compares busbar grid CO2 with
    #  tank-to-wheel diesel CO2.  The alternative grosses the grid factor up by
    #  transmission and distribution losses and takes diesel well-to-wheel.
    pars = _load_pars()
    losses = {"India": 0.17, "Chile": 0.05, "Mexico": 0.12, "Netherlands": 0.04}
    loss = losses.get(inst.country, 0.10)
    i2 = replace(inst,
                 ef={s_: inst.ef[s_] / (1.0 - loss) for s_ in inst.S},
                 ef_diesel=pars["ef_diesel_wtw"]["value"])
    record("emission_boundary", "delivered grid vs well-to-wheel diesel",
           M.bilevel_sd(i2, family, time_limit=time_limit, mip_gap=mip_gap),
           f"T&D losses {loss:.0%}; diesel {pars['ef_diesel_wtw']['value']} kgCO2/L")

    _write(f"sensitivity_{inst.name}.csv",
           ["parameter", "value", "exp_cost_usd", "exp_emissions_kgco2", "exp_grid_kwh",
            "n_electrified", "n_bays", "theta", "sigma", "note",
            "certified_mip_gap", "status"], rows)
    return {"rows": rows}


# =========================================================================== #
#  7. horizontal collaboration                                                 #
# =========================================================================== #
def collaboration(inst: Instance, family: str = "F4",
                  heterogeneities=(0.15, 0.35, 0.55, 0.75, 0.95),
                  time_limit: float = 900.0) -> dict:
    _log(f"collaboration {inst.name}")
    base = M.bilevel_sd(inst, family, time_limit=time_limit)
    main = CG.analyse(inst, family, leader=base["leader"], outdir=TAB)

    rows = []
    for h in heterogeneities:
        i2 = build_instance(inst.name, n_carriers=len(inst.C), heterogeneity=h)
        r = M.bilevel_sd(i2, family, time_limit=time_limit)
        g = CG.analyse(i2, family, leader=r["leader"])
        rows.append([h, g["standalone_total"], g["grand"], g["gain"], g["gain_pct"],
                     g["decomposition"]["pooling_gain"],
                     g["decomposition"]["platooning_gain"],
                     g["shapley_in_core"], g["least_core_eps"], g["core_nonempty"]])
    _write(f"collaboration_heterogeneity_{inst.name}.csv",
           ["heterogeneity", "standalone_total_usd", "grand_coalition_usd", "gain_usd",
            "gain_pct", "pooling_gain_usd", "platooning_gain_usd",
            "shapley_in_core", "least_core_eps", "core_nonempty"], rows)

    ncar = []
    for n in (2, 3, 4, 5):
        i2 = build_instance(inst.name, n_carriers=n)
        r = M.bilevel_sd(i2, family, time_limit=time_limit)
        g = CG.analyse(i2, family, leader=r["leader"])
        ncar.append([n, g["standalone_total"], g["grand"], g["gain"], g["gain_pct"],
                     g["shapley_in_core"], g["least_core_eps"]])
    _write(f"collaboration_ncarriers_{inst.name}.csv",
           ["n_carriers", "standalone_total_usd", "grand_coalition_usd", "gain_usd",
            "gain_pct", "shapley_in_core", "least_core_eps"], ncar)

    #  How much of the collaboration result rides on the entitlement rule by which
    #  a sub-coalition gets a share of the corridor's public capacity.  The rule is
    #  an assumption, not a measurement, so it is swept rather than defended.
    from .instance import ALLOCATION_RULES
    alloc = []
    for rule in ALLOCATION_RULES:
        g = CG.analyse(inst, family, leader=base["leader"], rule=rule)
        alloc.append([rule, g["standalone_total"], g["grand"], g["gain"],
                      g["gain_pct"], g["decomposition"]["pooling_gain"],
                      g["shapley_in_core"], g["least_core_eps"], g["core_nonempty"]])
        _log(f"   allocation rule {rule}: gain {g['gain']:,.0f} "
             f"({g['gain_pct']:.2f}%), core non-empty {g['core_nonempty']}")
    _write(f"collaboration_allocation_{inst.name}.csv",
           ["allocation_rule", "standalone_total_usd", "grand_coalition_usd",
            "gain_usd", "gain_pct", "pooling_gain_usd", "shapley_in_core",
            "least_core_eps", "core_nonempty"], alloc)
    return {"main": main, "heterogeneity": rows, "n_carriers": ncar,
            "allocation": alloc}


# =========================================================================== #
#  8. scalability                                                              #
# =========================================================================== #
def scalability(base_network: str = "vizag", family: str = "F4",
                edge_sizes=(3, 5, 7, 9, 11), corridors=(1, 2, 3),
                scenario_grid=((2, 2), (3, 3), (4, 4)),
                carriers=(2, 3, 5, 8),
                time_limit: float = 600.0, enum_limit_edges: int = 7) -> dict:
    """Grow the instance along four axes and compare the exact methods."""
    _log("scalability study")
    rows = []

    def run(inst, label, do_enum=False):
        sd = M.bilevel_sd(inst, family, time_limit=time_limit)
        kkt = M.bilevel_kkt(inst, family, time_limit=time_limit)
        en = None
        if do_enum and len(inst.E) <= enum_limit_edges:
            try:
                en = M.enumerate_leader(inst, family, max_designs=2 ** enum_limit_edges,
                                        time_limit=time_limit)
            except Exception as exc:      # pragma: no cover - defensive
                _log(f"   enumeration failed: {exc}")
        agree = ""
        if sd.get("obj") is not None and kkt.get("obj") is not None:
            agree = f"{abs(sd['obj'] - kkt['obj']) / max(1.0, abs(sd['obj'])):.2e}"
        agree_en = ""
        if en and en.get("obj") is not None and sd.get("obj") is not None:
            agree_en = f"{abs(sd['obj'] - en['obj']) / max(1.0, abs(sd['obj'])):.2e}"
        rows.append([label, len(inst.E), len(inst.arcs), len(inst.C), len(inst.S),
                     round(SC.design_space_log10(inst, family), 1),
                     sd.get("n_bin"), sd.get("n_var"), sd.get("n_con"),
                     sd.get("runtime"), sd.get("status"), sd.get("obj"),
                     kkt.get("n_bin"), kkt.get("runtime"), kkt.get("status"),
                     kkt.get("obj"), agree,
                     (en or {}).get("runtime"), (en or {}).get("designs"),
                     (en or {}).get("obj"), agree_en])
        _log(f"   {label}: SD {sd.get('runtime', 0):.1f}s ({sd.get('status')}), "
             f"KKT {kkt.get('runtime', 0):.1f}s ({kkt.get('status')})"
             + (f", ENUM {en['runtime']:.1f}s" if en else ""))

    full = build_instance(base_network, n_carriers=3)
    for k in edge_sizes:
        run(SC.sub_network(full, k), f"edges={k}", do_enum=(k <= enum_limit_edges))
    for k in corridors:
        if k == 1:
            continue
        run(SC.multi_corridor(full, k), f"corridors={k}")
    for (nd, ng) in scenario_grid:
        inst = SC.with_scenarios(base_network, nd, ng, n_carriers=3)
        run(inst, f"scenarios={nd * ng}")
    for nc in carriers:
        run(SC.with_carriers(full, nc), f"carriers={nc}")

    _write("scalability.csv",
           ["instance", "n_edges", "n_arcs", "n_carriers", "n_scenarios",
            "log10_design_space", "sd_binaries", "sd_variables", "sd_constraints",
            "sd_runtime_s", "sd_status", "sd_objective",
            "kkt_binaries", "kkt_runtime_s", "kkt_status", "kkt_objective",
            "sd_vs_kkt_rel_gap", "enum_runtime_s", "enum_designs", "enum_objective",
            "sd_vs_enum_rel_gap"], rows)
    return {"rows": rows}


# =========================================================================== #
#  9. when does making the charge state-contingent actually pay?               #
# =========================================================================== #
def state_contingency_value(inst: Instance, time_limit: float = 900.0,
                            sccs=(0.12, 0.19, 0.34, 0.80),
                            spreads=(1.0, 2.0, 4.0),
                            mip_gap: float = 0.0) -> dict:
    """Compare a state-blind charge (F3) with a state-contingent one (F4).

    Theorem 2 gives a charge that makes the coalition's objective *identical* to
    the social objective; a state-blind charge cannot do that unless the grid
    emission factor is the same in every state.  Identical objectives are
    sufficient for the first best but not necessary, though: because the
    follower's response is piecewise constant in the charge, a single level can
    happen to induce the socially optimal response in every scenario.  This
    experiment locates the region where that stops happening -- where the states
    are far enough apart, and carbon expensive enough, that one number cannot
    serve for both.

    The carbon prices swept are the low, central and high values of
    ``data/parameters.csv`` plus one stress level above that range; the spread
    multiplier widens the distance between the grid states around their mean
    while holding the mean fixed, so a spread of one is the calibrated instance.
    Every row records whether all three of its solves were certified optimal and
    whether the resulting gaps respect ``gap(F4) <= gap(F3)``, which must hold
    because F3 is a restriction of F4; no claim is drawn from a row that fails
    either test.
    """
    _log(f"value of state contingency {inst.name}")
    rows = []
    ef_mid = sum(inst.prob[s] * inst.ef[s] for s in inst.S)
    for scc in sccs:
        for spread in spreads:
            ef = {s: max(0.0, ef_mid + spread * (inst.ef[s] - ef_mid)) for s in inst.S}
            i2 = replace(inst, w_emis=scc, ef=ef)
            #  rebuild the charge menus so that both families can reach the
            #  Pigouvian levels of Theorem 2 for the widened states
            th = scc * i2.ef_diesel * i2.f_diesel
            sig = sorted({round(scc * ef[s] + i2.w_grid, 6) for s in i2.S})
            i2 = replace(i2,
                         theta_menu=sorted(set(i2.theta_menu) | {round(th, 6)}),
                         sigma_menu=sorted(set(i2.sigma_menu) | set(sig)))
            cen = M.centralized(i2, time_limit=time_limit, mip_gap=mip_gap)
            f3 = M.bilevel_sd(i2, "F3", time_limit=time_limit, mip_gap=mip_gap)
            f4 = M.bilevel_sd(i2, "F4", time_limit=time_limit, mip_gap=mip_gap)
            g3 = (f3["obj"] - cen["obj"]) if f3.get("obj") else None
            g4 = (f4["obj"] - cen["obj"]) if f4.get("obj") else None
            #  F3 is a restriction of F4, so gap(F4) <= gap(F3) must hold.  If a
            #  solve stopped on its time limit the incumbent can violate that, and
            #  such a row is recorded as uncertified rather than quietly reported.
            certified = all(r.get("certified") for r in (cen, f3, f4))
            consistent = (g3 is not None and g4 is not None
                          and g4 <= g3 + 1e-6 * max(1.0, abs(cen["obj"])))
            rows.append([scc, spread, round(min(ef.values()), 4), round(max(ef.values()), 4),
                         cen["obj"], f3.get("obj"), f4.get("obj"), g3, g4,
                         (100.0 * g3 / cen["obj"]) if g3 is not None else None,
                         (100.0 * g4 / cen["obj"]) if g4 is not None else None,
                         _fmt(f3.get("sigma") or {}), _fmt(f4.get("sigma") or {}),
                         certified, consistent,
                         cen.get("status"), f3.get("status"), f4.get("status"),
                         f3.get("mip_gap"), f4.get("mip_gap")])
            _log(f"   scc={scc} spread={spread}: gap F3={g3} F4={g4} "
                 f"certified={certified} consistent={consistent} "
                 f"[{cen.get('status')}/{f3.get('status')}/{f4.get('status')}]")
    _write(f"state_contingency_{inst.name}.csv",
           ["social_cost_of_carbon", "grid_state_spread", "ef_min", "ef_max",
            "first_best", "cost_F3", "cost_F4", "gap_F3", "gap_F4",
            "gap_F3_pct", "gap_F4_pct", "sigma_F3", "sigma_F4",
            "all_certified", "theory_consistent",
            "status_first_best", "status_F3", "status_F4",
            "mip_gap_F3", "mip_gap_F4"], rows)
    return {"rows": rows}


# =========================================================================== #
# 10. robustness of the collaboration result to the carrier-split seed         #
# =========================================================================== #
def collaboration_seeds(network: str = "vizag", n_carriers: int = 3,
                        seeds=(20260909, 11, 202, 3003, 40404, 5, 66, 777, 8888, 99),
                        family: str = "F4", time_limit: float = 600.0) -> dict:
    """Re-draw the carrier split and re-run the cooperative game.

    The carrier-level split of a corridor's volume is the one input no public
    source reports, so a single draw of it is not evidence.  This repeats the
    whole analysis over ten independent draws and reports the distribution of the
    gain, of its decomposition and of core stability.
    """
    _log("collaboration seed robustness")
    rows = []
    for sd in seeds:
        inst = build_instance(network, n_carriers=n_carriers, seed=sd)
        r = M.bilevel_sd(inst, family, time_limit=time_limit)
        g = CG.analyse(inst, family, leader=r["leader"])
        d = g["decomposition"]
        tot = d["total_gain"] or 1.0
        rows.append([sd, g["standalone_total"], g["grand"], g["gain"], g["gain_pct"],
                     100.0 * d["pooling_gain"] / tot, 100.0 * d["platooning_gain"] / tot,
                     g["shapley_in_core"], g["least_core_eps"], g["core_nonempty"]])
        _log(f"   seed {sd}: gain {g['gain']:,.0f} ({g['gain_pct']:.3f}%), "
             f"core {g['core_nonempty']}")
    import statistics as st
    gains = [r[4] for r in rows]
    summary = {"mean_gain_pct": st.mean(gains), "sd_gain_pct": st.pstdev(gains),
               "min_gain_pct": min(gains), "max_gain_pct": max(gains),
               "core_always_nonempty": all(r[9] for r in rows),
               "shapley_always_in_core": all(r[7] for r in rows)}
    rows.append(["MEAN", "", "", "", summary["mean_gain_pct"], "", "", "", "", ""])
    rows.append(["SD", "", "", "", summary["sd_gain_pct"], "", "", "", "", ""])
    _write(f"collaboration_seeds_{network}.csv",
           ["seed", "standalone_total_usd", "grand_coalition_usd", "gain_usd",
            "gain_pct", "pooling_share_pct", "platooning_share_pct",
            "shapley_in_core", "least_core_eps", "core_nonempty"], rows)
    return summary


# =========================================================================== #
# 11. in-sample stability of the scenario tree                                 #
# =========================================================================== #
def scenario_stability(network: str = "vizag", n_carriers: int = 3,
                       splits=(1, 2, 3), delta: float = 0.15,
                       family: str = "F4", time_limit: float = 600.0) -> dict:
    """Refine the scenario tree while holding its marginals fixed.

    Each of the four calibrated states is split into ``k`` equiprobable
    sub-states whose demand multipliers are symmetric about the state's own
    multiplier, so the mean and the state probabilities are unchanged and the
    objectives are directly comparable.  If the leader's decision and objective
    are stable as ``k`` grows, four states are enough to represent the
    uncertainty; if they are not, the paper should say so.
    """
    _log("scenario-tree stability")
    base = build_instance(network, n_carriers=n_carriers)
    rows = []
    for k in splits:
        offs = [0.0] if k == 1 else [delta * (2 * i / (k - 1) - 1) for i in range(k)]
        S, prob, price, ef, gav, DI, DE = [], {}, {}, {}, {}, {}, {}
        for s in base.S:
            for i, off in enumerate(offs):
                ns = f"{s}.{i}" if k > 1 else s
                S.append(ns)
                prob[ns] = base.prob[s] / k
                price[ns] = base.price[s]
                ef[ns] = base.ef[s]
                gav[ns] = base.Gavail[s]
                for c in base.C:
                    for n in base.Dn:
                        DI[(c, n, ns)] = round(base.DI[(c, n, s)] * (1 + off), 4)
                        DE[(c, n, ns)] = round(base.DE[(c, n, s)] * (1 + off), 4)
        inst = replace(base, S=S, prob=prob, price=price, ef=ef, Gavail=gav,
                       DI=DI, DE=DE)
        r = M.bilevel_sd(inst, family, time_limit=time_limit)
        cen = M.centralized(inst, time_limit=time_limit)
        rows.append([k, len(S), r.get("obj"), cen.get("obj"),
                     (r.get("obj") or 0) - (cen.get("obj") or 0),
                     r.get("n_electrified"), sum((r.get("bays") or {}).values()),
                     r.get("exp_emis"), r.get("runtime")])
        _log(f"   {len(S)} scenarios: obj {r.get('obj')}")
    _write(f"scenario_stability_{network}.csv",
           ["subsplits", "n_scenarios", "cost_F4", "cost_first_best", "gap",
            "n_electrified", "n_bays", "exp_emissions_kgco2", "runtime_s"], rows)
    return {"rows": rows}
