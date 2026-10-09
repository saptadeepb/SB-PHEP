"""
cooperative_game.py
===================
Horizontal collaboration among the carriers, analysed as a cooperative cost
game.

What the carriers actually gain by cooperating in this model is concrete rather
than notional.  Their import and export portfolios differ across hinterland
nodes, so at a node where one carrier releases empty containers and another
needs them, a coalition can *match them in place* while stand-alone carriers
must each reposition their own boxes.  On top of that, a coalition puts more
trucks on the same arc at the same time and can therefore form more platoons.
Both effects are endogenous outcomes of the lower-level LP; nothing about the
size of the gain is assumed.

Every characteristic value is an exact LP optimum, so the game is computed
exactly.  Stability is tested by solving the core linear program, not merely by
checking the Shapley allocation against a handful of coalitions.
"""
from __future__ import annotations

import csv
import os
from itertools import combinations
from math import factorial
from typing import Dict, FrozenSet, List

import pyomo.environ as pyo

from . import models as M
from .instance import Instance, sub_instance


def characteristic_costs(inst: Instance, leader: dict, family: str = "F4",
                         progress: bool = False,
                         rule: str = "box_km") -> Dict[FrozenSet[str], float]:
    """Expected annual private operating cost of every coalition.

    ``rule`` is the entitlement rule by which a sub-coalition receives a share of
    the corridor's public capacity; see :func:`instance.sub_instance`.
    """
    players = list(inst.C)
    cost: Dict[FrozenSet[str], float] = {frozenset(): 0.0}
    for k in range(1, len(players) + 1):
        for K in combinations(players, k):
            sub = sub_instance(inst, K, rule=rule)
            tot = 0.0
            for s in inst.S:
                obj, _info = M.follower_lp(sub, s, leader, family)
                if obj is None:
                    raise RuntimeError(f"coalition {K} infeasible in scenario {s}")
                tot += inst.prob[s] * obj
            cost[frozenset(K)] = inst.H * tot
            if progress:
                print(f"    c({{{','.join(K)}}}) = {cost[frozenset(K)]:,.0f}")
    return cost


def shapley_value(players: List[str], cost: Dict[FrozenSet[str], float]) -> Dict[str, float]:
    n = len(players)
    phi = {i: 0.0 for i in players}
    for i in players:
        others = [p for p in players if p != i]
        for k in range(len(others) + 1):
            for T in combinations(others, k):
                Ts = frozenset(T)
                w = factorial(len(Ts)) * factorial(n - len(Ts) - 1) / factorial(n)
                phi[i] += w * (cost[Ts | {i}] - cost[Ts])
    return phi


def core_lp(players: List[str], cost: Dict[FrozenSet[str], float]):
    """Solve  min eps  s.t.  sum_{i in K} x_i <= c(K) + eps for all K,  sum x = c(N).

    ``eps <= 0`` certifies a non-empty core; the optimal ``eps`` is the least-core
    value and measures how far the game is from stability when it is positive.
    """
    N = frozenset(players)
    m = pyo.ConcreteModel()
    m.P = pyo.Set(initialize=players, ordered=True)
    m.x = pyo.Var(m.P, domain=pyo.Reals)
    m.eps = pyo.Var(domain=pyo.Reals)
    m.eff = pyo.Constraint(expr=sum(m.x[i] for i in players) == cost[N])
    m.con = pyo.ConstraintList()
    for k in range(1, len(players)):
        for K in combinations(players, k):
            m.con.add(sum(m.x[i] for i in K) <= cost[frozenset(K)] + m.eps)
    m.OBJ = pyo.Objective(expr=m.eps, sense=pyo.minimize)
    res, tc, ok = M._solve(m)
    if not ok:
        return {"status": tc}
    return {"status": tc, "eps": pyo.value(m.eps),
            "alloc": {i: pyo.value(m.x[i]) for i in players},
            #  the tolerance is relative to the grand coalition's cost, because
            #  the excess is an unnormalised annual money amount
            "core_nonempty": pyo.value(m.eps) <= 1e-9 * max(1.0, abs(cost[N]))}


def core_check(players, cost, alloc, tol: float = 1e-6):
    """Excesses of the given allocation over every coalition's stand-alone cost."""
    worst, violations = -float("inf"), []
    for k in range(1, len(players) + 1):
        for K in combinations(players, k):
            Ks = frozenset(K)
            exc = sum(alloc[i] for i in K) - cost[Ks]
            worst = max(worst, exc)
            if exc > tol:
                violations.append((tuple(sorted(K)), sum(alloc[i] for i in K), cost[Ks]))
    return (not violations), violations, worst


def analyse(inst: Instance, family: str = "F4", leader: dict | None = None,
            outdir: str | None = None, progress: bool = False,
            rule: str = "box_km") -> dict:
    """Full cooperative analysis at the leader's grand-coalition optimum."""
    if leader is None:
        gc = M.bilevel_sd(inst, family)
        if gc.get("obj") is None:
            raise RuntimeError("leader problem did not solve")
        leader = gc["leader"]
    players = list(inst.C)
    cost = characteristic_costs(inst, leader, family, progress=progress, rule=rule)
    N = frozenset(players)

    standalone = sum(cost[frozenset([i])] for i in players)
    grand = cost[N]
    gain = standalone - grand
    phi = shapley_value(players, cost)
    in_core, violations, worst_excess = core_check(players, cost, phi)
    clp = core_lp(players, cost)

    #  decomposition of the gain: how much comes from pooling empties and how
    #  much from consolidating platoons.  Obtained by re-solving the grand
    #  coalition with each channel switched off in turn.
    decomp = _decompose_gain(inst, leader, family, cost)

    out = {"players": players, "cost": {tuple(sorted(k)): v for k, v in cost.items()},
           "standalone_total": standalone, "grand": grand, "gain": gain,
           "gain_pct": 100.0 * gain / standalone if standalone else 0.0,
           "shapley": phi, "shapley_in_core": in_core,
           "shapley_worst_excess": worst_excess, "violations": violations,
           "least_core_eps": clp.get("eps"), "core_nonempty": clp.get("core_nonempty"),
           "core_allocation": clp.get("alloc"), "decomposition": decomp,
           "leader": leader, "family": family}
    if outdir:
        _write(out, inst, outdir)
    return out


def _decompose_gain(inst: Instance, leader: dict, family: str,
                    cost: Dict[FrozenSet[str], float]) -> dict:
    """Decompose the collaboration gain by switching platooning off.

    Only one counterfactual is computed, and it is reported for what it is.
    With the platoon coordination cost set prohibitively high, no platoon forms
    and the whole remaining gain comes from pooling empty containers; call that
    ``gain_without_platooning``.  The difference between the full gain and that
    number is everything platooning contributes, including its interaction with
    pooling, and is reported as ``platooning_and_interaction``.  The two are not
    separable channels and the paper does not present them as such.
    """
    from dataclasses import replace

    players = list(inst.C)
    grand = cost[frozenset(players)]
    standalone = sum(cost[frozenset([i])] for i in players)

    # platooning off: c_plat set so high that no platoon ever forms
    hi = replace(inst, c_plat=1e6)
    tot = 0.0
    for s in inst.S:
        obj, _ = M.follower_lp(hi, s, leader, family)
        if obj is None:
            raise RuntimeError(f"platooning-off counterfactual infeasible in scenario {s}")
        tot += inst.prob[s] * obj
    grand_np = inst.H * tot
    sa_np = 0.0
    for i in players:
        sub = sub_instance(hi, [i])
        t = 0.0
        for s in inst.S:
            obj, _ = M.follower_lp(sub, s, leader, family)
            if obj is None:
                raise RuntimeError(f"platooning-off counterfactual infeasible for {i}")
            t += inst.prob[s] * obj
        sa_np += inst.H * t
    pooling_gain = sa_np - grand_np
    return {"total_gain": standalone - grand,
            "gain_without_platooning": pooling_gain,
            "platooning_and_interaction": (standalone - grand) - pooling_gain,
            # kept under the old keys as well so that result files stay readable
            "pooling_gain": pooling_gain,
            "platooning_gain": (standalone - grand) - pooling_gain,
            "standalone_no_platoon": sa_np, "grand_no_platoon": grand_np}


def _write(out: dict, inst: Instance, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, f"coalition_costs_{inst.name}.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["coalition", "cost_usd_per_yr"])
        for k in sorted(out["cost"], key=lambda t: (len(t), t)):
            if not k:
                continue
            w.writerow(["{" + ",".join(k) + "}", round(out["cost"][k], 2)])
    with open(os.path.join(outdir, f"shapley_{inst.name}.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["carrier", "standalone_cost", "shapley_cost", "saving",
                    "saving_pct", "core_allocation"])
        for i in out["players"]:
            sa = out["cost"][(i,)]
            ca = (out["core_allocation"] or {}).get(i, "")
            w.writerow([i, round(sa, 2), round(out["shapley"][i], 2),
                        round(sa - out["shapley"][i], 2),
                        round(100 * (sa - out["shapley"][i]) / sa, 4),
                        round(ca, 2) if ca != "" else ""])
        w.writerow(["TOTAL", round(out["standalone_total"], 2), round(out["grand"], 2),
                    round(out["gain"], 2), round(out["gain_pct"], 4), ""])
