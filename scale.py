"""
scale.py
========
Instance-size controls for the scalability study.

Whether an exact method is needed depends on how large the leader's design space
actually is, and that is a question to be answered rather than asserted.  This
module makes it testable: it produces a family of instances whose electrifiable
design space grows from 2^3 to 2^40 and whose scenario tree grows from 6 to 64, all
from the same authenticated corridor data, so that the exact methods can be compared
on a common footing.

Two directions of growth are supported.

*Shrinking* takes a connected sub-corridor of a real network (a breadth-first
subtree from the port), which keeps every arc length and demand weight
authentic.

*Growing* replicates the corridor into a multi-corridor regional network: real
port-hinterland systems are exactly that, several corridors sharing a port and a
grid, so the enlarged instances are structurally faithful rather than random.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, List, Sequence, Tuple

from .instance import DEMAND_LEVELS, GRID_STATES, Instance, build_instance


# --------------------------------------------------------------------------- #
#  scenario-tree growth                                                        #
# --------------------------------------------------------------------------- #
def with_scenarios(network: str, n_demand: int, n_grid: int, **kw) -> Instance:
    """Build an instance with a finer scenario tree.

    Demand levels are taken from the three calibrated levels and, beyond three,
    are interpolated on a uniform grid between the lowest and highest; grid
    states beyond the three published ones interpolate the emission factor
    between the clean and marginal anchors.  Every added state therefore stays
    inside the range that the published data support.
    """
    base = build_instance(network, demand_levels=("L", "M", "H")[:min(3, n_demand)],
                          grid_states=("clean", "average", "marginal")[:min(3, n_grid)], **kw)
    if n_demand <= 3 and n_grid <= 3:
        return base

    dl = _interp_levels([DEMAND_LEVELS[k] for k in ("L", "M", "H")], n_demand)
    ef_lo, ef_hi = base.ef[min(base.ef, key=base.ef.get)], base.ef[max(base.ef, key=base.ef.get)]
    pr_lo, pr_hi = base.price[min(base.price, key=base.price.get)], \
        base.price[max(base.price, key=base.price.get)]
    ga_lo, ga_hi = min(base.Gavail.values()), max(base.Gavail.values())
    gl = [i / (n_grid - 1) if n_grid > 1 else 0.0 for i in range(n_grid)]

    S, prob, price, ef, Gav = [], {}, {}, {}, {}
    DI, DE = {}, {}
    ref_d = list(base.S)[0].split("-")[0]
    for i, dmul in enumerate(dl):
        for j, t in enumerate(gl):
            s = f"D{i}-G{j}"
            S.append(s)
            prob[s] = (1.0 / len(dl)) * (1.0 / len(gl))
            ef[s] = round(ef_lo + t * (ef_hi - ef_lo), 6)
            price[s] = round(pr_lo + t * (pr_hi - pr_lo), 6)
            Gav[s] = round(ga_hi + t * (ga_lo - ga_hi), 2)
            for c in base.C:
                for n in base.Dn:
                    base_di = base.DI[(c, n, base.S[0])] / DEMAND_LEVELS[ref_d]
                    base_de = base.DE[(c, n, base.S[0])] / DEMAND_LEVELS[ref_d]
                    DI[(c, n, s)] = round(base_di * dmul, 3)
                    DE[(c, n, s)] = round(base_de * dmul, 3)
    return replace(base, S=S, prob=prob, price=price, ef=ef, Gavail=Gav, DI=DI, DE=DE)


def _interp_levels(anchors: Sequence[float], n: int) -> List[float]:
    lo, hi = min(anchors), max(anchors)
    if n == 1:
        return [(lo + hi) / 2]
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


# --------------------------------------------------------------------------- #
#  network growth and shrinkage                                                #
# --------------------------------------------------------------------------- #
def sub_network(inst: Instance, n_edges: int) -> Instance:
    """Keep a connected sub-corridor with at most ``n_edges`` physical links."""
    if n_edges >= len(inst.edges):
        return inst
    keep_edges: List[Tuple[str, str]] = []
    seen = {inst.o}
    frontier = [inst.o]
    while frontier and len(keep_edges) < n_edges:
        n = frontier.pop(0)
        for e in inst.edges:
            if len(keep_edges) >= n_edges:
                break
            if e in keep_edges:
                continue
            if e[0] == n and e[1] not in seen:
                keep_edges.append(e); seen.add(e[1]); frontier.append(e[1])
            elif e[1] == n and e[0] not in seen:
                keep_edges.append(e); seen.add(e[0]); frontier.append(e[0])
    return _restrict(inst, keep_edges, seen)


def _restrict(inst: Instance, keep_edges, keep_nodes) -> Instance:
    arcs = [a for a in inst.arcs if inst.edge_of_arc[a] in keep_edges]
    nodes = [n for n in inst.nodes if n in keep_nodes]
    Dn = [n for n in inst.Dn if n in keep_nodes]
    if not Dn:
        raise ValueError("sub-network has no demand node")
    dist = {a: inst.dist[a] for a in arcs}
    eoa = {a: inst.edge_of_arc[a] for a in arcs}
    aoe = {e: [a for a in arcs if eoa[a] == e] for e in keep_edges}
    E = [e for e in inst.E if e in keep_edges]
    #  re-scale the retained nodes' demand so that total corridor volume is
    #  preserved: the sub-corridor stands for the whole port's road traffic.
    old_tot = sum(inst.DI[(c, n, s)] + inst.DE[(c, n, s)]
                  for c in inst.C for n in inst.Dn for s in inst.S)
    new_tot = sum(inst.DI[(c, n, s)] + inst.DE[(c, n, s)]
                  for c in inst.C for n in Dn for s in inst.S)
    k = (old_tot / new_tot) if new_tot > 0 else 1.0
    DI = {(c, n, s): round(inst.DI[(c, n, s)] * k, 3)
          for c in inst.C for n in Dn for s in inst.S}
    DE = {(c, n, s): round(inst.DE[(c, n, s)] * k, 3)
          for c in inst.C for n in Dn for s in inst.S}
    Cap = {a: inst.Cap[a] for a in arcs}
    return replace(inst, nodes=nodes, Dn=Dn, arcs=arcs, edges=list(keep_edges), E=E,
                   dist=dist, edge_of_arc=eoa, arcs_of_edge=aoe, DI=DI, DE=DE, Cap=Cap)


def multi_corridor(inst: Instance, k: int) -> Instance:
    """Replicate the hinterland ``k`` times around the same port and grid.

    Physical arc lengths, demand weights and the shared scenario grid budget are
    kept; the copies represent the several corridors that radiate from a real
    gateway port.  Demand per copy is the corridor's own volume, so total port
    throughput scales with ``k`` while the *shared* grid headroom does not --
    which is what makes the larger instances genuinely harder rather than merely
    bigger.
    """
    if k <= 1:
        return inst
    nodes, arcs, edges, E = [inst.o], [], [], []
    dist, eoa = {}, {}
    Dn, Cap = [], {}
    DI, DE, node_info = {}, {}, {inst.o: inst.node_info[inst.o]}
    for r in range(k):
        sfx = "" if r == 0 else f"#{r}"
        rn = {n: (n if n == inst.o else f"{n}{sfx}") for n in inst.nodes}
        for n in inst.nodes:
            if n == inst.o:
                continue
            nodes.append(rn[n])
            node_info[rn[n]] = inst.node_info[n]
            if n in inst.Dn:
                Dn.append(rn[n])
        for e in inst.edges:
            ne = (rn[e[0]], rn[e[1]])
            edges.append(ne)
            if e in inst.E:
                E.append(ne)
            for a, na in zip(inst.arcs_of_edge[e], [ne, (ne[1], ne[0])]):
                arcs.append(na)
                dist[na] = inst.dist[a]
                eoa[na] = ne
                Cap[na] = inst.Cap[a]
        for c in inst.C:
            for n in inst.Dn:
                for s in inst.S:
                    DI[(c, rn[n], s)] = inst.DI[(c, n, s)]
                    DE[(c, rn[n], s)] = inst.DE[(c, n, s)]
    aoe = {e: [a for a in arcs if eoa[a] == e] for e in edges}
    K_fix = {e: list(inst.K_fix.values())[0] for e in E}
    K_km = {e: list(inst.K_km.values())[0] for e in E}
    return replace(inst, nodes=nodes, Dn=Dn, arcs=arcs, edges=edges, E=E, dist=dist,
                   edge_of_arc=eoa, arcs_of_edge=aoe, DI=DI, DE=DE, Cap=Cap,
                   node_info=node_info, K_fix=K_fix, K_km=K_km)


def with_carriers(inst: Instance, n: int, seed: int = 20260909) -> Instance:
    """Re-split the same corridor volume among ``n`` heterogeneous carriers."""
    import numpy as np
    rng = np.random.default_rng(seed + n)
    tot_DI = {(n_, s): sum(inst.DI[(c, n_, s)] for c in inst.C)
              for n_ in inst.Dn for s in inst.S}
    tot_DE = {(n_, s): sum(inst.DE[(c, n_, s)] for c in inst.C)
              for n_ in inst.Dn for s in inst.S}
    C = [f"c{i + 1}" for i in range(n)]
    shares = rng.dirichlet(np.full(n, 6.0))
    tilt = {n_: rng.dirichlet(np.full(n, 1.5)) for n_ in inst.Dn}
    DI, DE = {}, {}
    for i, c in enumerate(C):
        for n_ in inst.Dn:
            w = shares[i] * tilt[n_][i]
            den = float(sum(shares[j] * tilt[n_][j] for j in range(n)))
            f = w / den if den > 0 else 1.0 / n
            for s in inst.S:
                DI[(c, n_, s)] = round(tot_DI[(n_, s)] * f, 3)
                DE[(c, n_, s)] = round(tot_DE[(n_, s)] * f, 3)
    return replace(inst, C=C, DI=DI, DE=DE)


def size_label(inst: Instance) -> str:
    return (f"|E|={len(inst.E)} |A|={len(inst.arcs)} |C|={len(inst.C)} |S|={len(inst.S)}")


def design_space_log10(inst: Instance, family: str = "F4") -> float:
    """log10 of the number of distinct leader configurations.

    Counted exactly, which takes some care.

    *Infrastructure.*  Per edge the leader picks ``(y_e, m_e)`` subject to
    ``m_e <= mbar * y_e``, so the admissible pairs are ``(0, 0)`` and
    ``(1, m)`` for ``m`` in ``0..mbar``: ``mbar + 2`` per edge, not
    ``2 * (mbar + 1)``, because a site with no charger and no site at all are the
    same configuration of the infrastructure decision counted twice.

    *Charges.*  Neither charge is indexed by edge.  Multiplying the per-kilometre
    menu once per edge would overstate the count by eight orders of magnitude; both
    charges are corridor-wide: one level each for F1 and F2 (no per-kWh charge at
    all), one of each for F3, and one of each *per scenario* for F4.
    """
    n = len(inst.E)
    n_theta = max(2, len(inst.theta_menu))
    n_sigma = max(2, len(inst.sigma_menu))
    if family == "F0":
        charge = 0.0
    elif family in ("F1", "F2"):
        charge = math.log10(n_theta)
    elif family == "F3":
        charge = math.log10(n_theta) + math.log10(n_sigma)
    else:                                              # F4: one level per state
        charge = len(inst.S) * (math.log10(n_theta) + math.log10(n_sigma))
    return n * math.log10(inst.n_bays_max + 2) + charge
