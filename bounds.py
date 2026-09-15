"""
bounds.py
=========
Provably valid bounds for the single-level reformulations.

Choosing big-M constants for a bilevel program is not a matter of taste: too
small and the reformulation silently cuts off the true optimum, too large and
the relaxation collapses.  Kleinert, Labbe, Plein and Schmidt (2020) show that
verifying a big-M is correct is itself NP-hard in general.  The reformulation
used in this paper is designed so that the question barely arises:

* the restriction "electric operation only on an electrified edge" needs no
  constraint at all: the charging-capacity row together with the leader's own
  ``m_e <= mbar * y_e`` coupling already implies it, so there is no big-M in the
  lower level (Lemma 2 of the paper);
* consequently the only right-hand side that depends on the leader is the
  charging-capacity row, so the strong-duality reformulation needs a valid upper
  bound on exactly **one** family of duals -- the marginal value of installed
  charging capacity -- which :func:`charging_dual_bound` derives in closed form.

The KKT/big-M baseline, by contrast, needs a bound on *every* dual and *every*
primal slack.  Those are supplied here too, so that the comparison in the
scalability study is a fair one, but they are exactly the constants the proposed
route avoids.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from . import lp as L
from .instance import Instance

_CACHE: Dict[tuple, object] = {}


def _sig(inst: Instance, family: str) -> tuple:
    """A signature that captures *everything* the bounds depend on.

    Keying the cache on a handful of scalars would let it return
    the bounds of one instance for another with the same totals but a different
    network -- and, because the bound vector is indexed positionally by row, a
    collision would have silently attached a charging bound to a demand row.
    The signature now includes the full structure, and the caller asserts the
    length of what it gets back.
    """
    return (inst.name, inst.country, family,
            tuple(inst.C), tuple(inst.S), tuple(inst.nodes), tuple(inst.Dn),
            tuple(inst.arcs), tuple(inst.edges), tuple(inst.E),
            tuple(round(inst.dist[a], 6) for a in inst.arcs),
            tuple(round(inst.Cap[a], 6) for a in inst.arcs),
            inst.n_bits, round(inst.module_kwh, 6), round(inst.resource_share, 9),
            tuple(round(v, 8) for v in inst.theta_menu),
            tuple(round(v, 8) for v in inst.sigma_menu),
            round(inst.w_emis, 8), round(inst.w_grid, 8), round(inst.p_diesel, 8),
            round(inst.f_diesel, 8), round(inst.e_elec, 8), round(inst.psave, 8),
            round(inst.c_plat, 6), round(inst.wage, 6), round(inst.PEN, 4),
            round(inst.ef_diesel, 8), round(inst.rho, 6),
            tuple(round(inst.Gavail[s], 6) for s in inst.S),
            tuple(round(inst.price[s], 8) for s in inst.S),
            tuple(round(inst.ef[s], 8) for s in inst.S),
            tuple(round(inst.DI[(c, n, s)], 6) for c in inst.C
                  for n in inst.Dn for s in inst.S),
            tuple(round(inst.DE[(c, n, s)], 6) for c in inst.C
                  for n in inst.Dn for s in inst.S))


# --------------------------------------------------------------------------- #
#  the one bound the proposed reformulation needs                              #
# --------------------------------------------------------------------------- #
def charging_dual_bound(inst: Instance, s: str, edge, family: str) -> float:
    """Valid upper bound on the dual of the charging-capacity row of ``edge``.

    Claim.  At any optimal dual solution of the follower LP in scenario ``s``,
    the multiplier of the charging-capacity row of edge ``e`` satisfies

        lambda_chg(e) <= max_{a in arcs(e)} max_{p in {0, 1}} R(a, p),

        R(a, p) = [ Delta(a) + p * DeltaPlat(a) ]
                  / [ e_elec * dist(a) * (1 - p * psave) ]

    where ``Delta(a)`` is the largest cost increase, over every leader decision,
    from serving one truck movement on ``a`` by diesel rather than electricity,
    and ``DeltaPlat(a)`` is the same quantity for its platoon unit.

    Proof.  The value function of the follower LP is convex and piecewise linear
    in the capacity ``g_e`` of the row, and the multiplier is a subgradient, so it
    is bounded above by the left difference quotient
    ``[v(g_e - eps) - v(g_e)] / eps`` for any ``eps > 0``.  We exhibit a feasible
    point for ``g_e - eps`` and bound its cost.  Take an optimal solution at
    ``g_e``; if no arc of ``e`` carries electric traction the row is slack and the
    multiplier is zero, so assume some arc ``a`` of ``e`` does.  Move an amount of
    traffic from ``xE_a`` to ``xD_a``, carrying with it the same platooned
    fraction ``p`` in which it was travelling, until ``eps`` kWh have been freed.
    This keeps the total movements on ``a`` unchanged, so ``eq:trucks``,
    ``eq:cap`` and the platoon rows (all three, since ``p`` is held fixed) are
    preserved; it only relaxes ``eq:grid``; it touches no other edge's charging
    row, because an arc belongs to exactly one edge; and no flow or demand
    variable moves, so the remaining rows are untouched.  Freeing one kWh this way
    requires ``1 / [e_elec * dist(a) * (1 - p * psave)]`` movements and costs at
    most ``Delta(a) + p * DeltaPlat(a)`` each, giving ``R(a, p)``.  Both numerator
    and denominator are affine in ``p``, so the ratio is maximised at an endpoint
    of ``[0, 1]``; taking the worst arc of ``e`` completes the bound.  QED

    Using the ``p = 1`` branch for every case would be valid but looser, by
    ``1 / (1 - psave)`` whenever the cheapest exchange is an unplatooned one.  Both
    branches are valid; the maximum of the two is the tighter valid bound and is
    what is returned.
    """
    best = 0.0
    for a in inst.arcs_of_edge[edge]:
        d = inst.dist[a]
        cD = L.const(inst.wage * d + inst.p_diesel * inst.f_diesel * d) \
            + L.charge_terms(inst, family, s, a, "xD")
        cE = L.const(inst.wage * d + inst.price[s] * inst.e_elec * d) \
            + L.charge_terms(inst, family, s, a, "xE")
        cpD = L.const(inst.c_plat - inst.psave * inst.p_diesel * inst.f_diesel * d) \
            + L.charge_terms(inst, family, s, a, "pD")
        cpE = L.const(inst.c_plat - inst.psave * inst.price[s] * inst.e_elec * d) \
            + L.charge_terms(inst, family, s, a, "pE")
        delta = max(L._menu_max(cD) - L._menu_min(cE), 0.0)
        delta_plat = max(L._menu_max(cpD) - L._menu_min(cpE), 0.0)
        for p in (0.0, 1.0):
            energy = inst.e_elec * d * (1.0 - p * inst.psave)
            if energy > 1e-9:
                best = max(best, (delta + p * delta_plat) / energy)
    #  Only the exchange argument is used: it is the one that is airtight,
    #  because the substitute movement stays on the same arc and therefore
    #  frees energy on exactly the edge whose capacity is being priced.  A
    #  bound derived from dropping the load at the unmet-demand penalty is
    #  numerically weaker on every instance we solve and is not needed.
    #
    #  ``best == 0`` is not degenerate: it says the diesel substitute is never
    #  more expensive than electricity under any leader decision, so capacity has
    #  no marginal value and zero is the correct bound.  A strictly positive
    #  tolerance is still returned so that the McCormick blocks do not pin the
    #  multiplier at exactly zero on a solver's rounding.
    return best * (1.0 + 1e-9) + 1e-6


def grid_dual_bound(inst: Instance, s: str, family: str) -> float:
    """Same argument applied to the system-wide charging headroom row."""
    return max(charging_dual_bound(inst, s, e, family) for e in inst.edges)


# --------------------------------------------------------------------------- #
#  full bound vectors                                                          #
# --------------------------------------------------------------------------- #
def dual_bounds_for(inst: Instance, family: str) -> Dict[str, List[float]]:
    """Upper bounds for every follower dual, per scenario.

    Rows whose right-hand side does not involve the leader do not need a bound
    for the strong-duality reformulation; they are given the analytic bound
    below anyway so that the same vector can serve the KKT baseline.
    """
    key = ("dual", _sig(inst, family))
    if key in _CACHE:
        cached = _CACHE[key]
        for s in inst.S:
            if len(cached[s]) != L.build_follower(inst, s, family).n_rows:
                raise AssertionError("cached bound vector has the wrong length")
        return cached                                        # type: ignore[return-value]

    out: Dict[str, List[float]] = {}
    for s in inst.S:
        flp = L.build_follower(inst, s, family)
        cmax = max(L._menu_max(t) for t in flp.cost)
        #  A generic valid bound for a row of a min-cost network-flow-like LP:
        #  no shadow price can exceed the cost of the most expensive way of
        #  satisfying one more unit of that row, and every requirement row can
        #  always be met by paying the unmet-demand penalty.
        generic = max(inst.PEN, cmax) * float(len(inst.nodes))
        b = []
        for r in flp.rows:
            if r.name.startswith("chgcap["):
                e = _edge_from_name(inst, r.name)
                b.append(charging_dual_bound(inst, s, e, family))
            elif r.name == "gridcap":
                b.append(grid_dual_bound(inst, s, family))
            elif r.name.startswith("import[") or r.name.startswith("export["):
                b.append(inst.PEN * 2.0)
            elif r.name.startswith("empty["):
                b.append(inst.PEN * 2.0)
            else:
                b.append(generic)
        out[s] = b
    _CACHE[key] = out
    return out


def slack_bounds_for(inst: Instance, family: str) -> Dict[str, List[float]]:
    """Upper bounds on every primal slack ``A_i x - b_i``, per scenario.

    Obtained from the variable box and the tightest leader-feasible right-hand
    side, hence valid for every leader decision by construction.
    """
    key = ("slack", _sig(inst, family))
    if key in _CACHE:
        return _CACHE[key]                                   # type: ignore[return-value]
    out: Dict[str, List[float]] = {}
    for s in inst.S:
        flp = L.build_follower(inst, s, family)
        b = []
        for r in flp.rows:
            hi = sum(max(c, 0.0) * flp.var_ub[j] for j, c in r.coef.items())
            lo_rhs = L._menu_min(r.rhs)
            b.append(max(hi - lo_rhs, 0.0) + 1.0)
        out[s] = b
    _CACHE[key] = out
    return out


def _edge_from_name(inst: Instance, name: str):
    inner = name[name.index("[") + 1: name.rindex("]")]
    for e in inst.edges:
        if str(e) == inner:
            return e
    raise KeyError(f"cannot resolve edge from row name {name!r}")


# --------------------------------------------------------------------------- #
#  empirical verification of the analytic bounds                               #
# --------------------------------------------------------------------------- #
def verify_bounds(inst: Instance, family: str, leaders, tol: float = 1e-6) -> dict:
    """Solve the follower LP at a set of leader decisions and check the bounds.

    The analytic bounds above are proved, not fitted; this routine is the
    belt-and-braces numerical check that the proofs were implemented correctly.

    It reports the largest observed dual as a fraction of its bound **per row
    family**, not only overall, because the two are easily confused and only one
    of them matters for the reformulation.  The bound on the system-wide headroom
    row is never imposed in the strong-duality model -- that row's right-hand side
    does not depend on the leader, so its dual is left free -- and the bounds on
    all the other families are imposed only in the KKT/big-M baseline.  The only
    bound the proposed formulation relies on, and the only one feeding a McCormick
    block, is the one on the ``chgcap`` rows, so ``max_ratio_chgcap`` is the
    figure that says how tight the formulation's own constant is.
    """
    from .models import follower_lp

    db = dual_bounds_for(inst, family)
    worst = 0.0
    per_family: Dict[str, float] = {}
    violations = []
    checked = 0
    for leader in leaders:
        for s in inst.S:
            obj, info = follower_lp(inst, s, leader, family, want_duals=True)
            if obj is None:
                continue
            rows = info["lp"].rows
            for i, dv in enumerate(info["duals"]):
                checked += 1
                bnd = db[s][i]
                fam = rows[i].name.split("[")[0] if i < len(rows) else "unknown"
                if bnd <= 0:
                    if dv > tol:
                        violations.append((s, i, dv, bnd))
                    continue
                ratio = dv / bnd
                worst = max(worst, ratio)
                per_family[fam] = max(per_family.get(fam, 0.0), ratio)
                if dv > bnd * (1 + 1e-6) + tol:
                    violations.append((s, i, dv, bnd))
    return {"checked": checked, "max_ratio": worst,
            "max_ratio_chgcap": per_family.get("chgcap", 0.0),
            "max_ratio_by_family": per_family,
            "violations": violations, "ok": not violations}
