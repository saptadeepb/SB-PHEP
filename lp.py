"""
lp.py
=====
A *symbolic* description of the carrier coalition's lower-level linear program.

The whole exactness argument of the paper rests on one structural fact, which
this module makes explicit and machine-checkable:

    for fixed leader decisions the followers solve

            min  c(w)^T x     s.t.   A x >= b(w),  x >= 0,

    where the constraint matrix ``A`` does **not** depend on the leader's
    decision ``w`` at all; the leader enters only through the cost vector
    ``c(w)`` and the right-hand side ``b(w)``, and does so *affinely in binary
    variables* because every leader instrument is discrete.

Because of that, both single-level reformulations used in the paper -- the
strong-duality one (``models.bilevel_sd``) and the KKT/big-M one
(``models.bilevel_kkt``) -- can be generated mechanically from the same object,
which removes the hand-derived stationarity conditions that are the usual source
of silent errors in bilevel papers.

Representation
--------------
``LeaderTerm`` is an affine function of the leader's binary variables:
``const + sum_k coef_k * bin_k`` where ``bin_k`` is identified by a hashable key.
Cost coefficients and right-hand sides are ``LeaderTerm``s; matrix entries are
plain floats.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Hashable, List, Tuple

from .instance import Instance

# ---- instrument families ---------------------------------------------------
#  F0 none              : no corridor charge at all
#  F1 flat              : uniform per-truck-km charge, no platoon discount
#  F2 waiver            : per-truck-km charge fully waived for platooned trucks
#                         (the instrument used in the earlier literature)
#  F3 discount          : platoon-*discounted* charge on diesel truck-km plus a
#                         per-kWh charging surcharge; both state-independent
#  F4 contingent        : as F3 but both instruments indexed to the realised
#                         grid state (the instrument proposed in this paper)
FAMILIES = ("F0", "F1", "F2", "F3", "F4")


@dataclass(frozen=True)
class LeaderTerm:
    const: float = 0.0
    lin: Tuple[Tuple[Hashable, float], ...] = ()

    def __add__(self, other: "LeaderTerm") -> "LeaderTerm":
        return LeaderTerm(self.const + other.const, self.lin + other.lin)

    def scaled(self, k: float) -> "LeaderTerm":
        return LeaderTerm(self.const * k, tuple((b, c * k) for b, c in self.lin))

    @property
    def is_const(self) -> bool:
        return not self.lin


CONST0 = LeaderTerm(0.0)


def const(v: float) -> LeaderTerm:
    return LeaderTerm(float(v))


@dataclass
class Row:
    """One constraint  sum_j a_j x_j  >=  rhs  (dual variable >= 0)."""
    coef: Dict[int, float]
    rhs: LeaderTerm
    name: str


@dataclass
class FollowerLP:
    """Lower-level LP for one scenario and one coalition."""
    scenario: str
    var_name: List[str] = field(default_factory=list)
    var_ub: List[float] = field(default_factory=list)
    cost: List[LeaderTerm] = field(default_factory=list)
    rows: List[Row] = field(default_factory=list)
    index: Dict[Hashable, int] = field(default_factory=dict)

    # -- construction ------------------------------------------------------ #
    def add_var(self, key: Hashable, name: str, ub: float, cost: LeaderTerm) -> int:
        j = len(self.var_name)
        self.index[key] = j
        self.var_name.append(name)
        self.var_ub.append(float(ub))
        self.cost.append(cost)
        return j

    def add_row(self, coef: Dict[int, float], rhs: LeaderTerm, name: str) -> int:
        self.rows.append(Row(dict(coef), rhs, name))
        return len(self.rows) - 1

    def add_eq(self, coef: Dict[int, float], rhs: LeaderTerm, name: str) -> None:
        """An equality, encoded as two >= rows so that every dual stays >= 0."""
        self.add_row(coef, rhs, name + "+")
        self.add_row({j: -c for j, c in coef.items()}, rhs.scaled(-1.0), name + "-")

    # -- introspection ----------------------------------------------------- #
    @property
    def n_vars(self) -> int:
        return len(self.var_name)

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    def leader_keys(self):
        keys = set()
        for t in self.cost:
            keys.update(b for b, _ in t.lin)
        for r in self.rows:
            keys.update(b for b, _ in r.rhs.lin)
        return keys


# --------------------------------------------------------------------------- #
#  charge structure                                                            #
# --------------------------------------------------------------------------- #
def charge_terms(inst: Instance, family: str, s: str, a, kind: str):
    """Leader-dependent part of the objective coefficient of a follower variable.

    ``kind`` in {'xE','xD','pE','pD'}; the returned :class:`LeaderTerm` is the
    charge levied per unit of that variable on arc ``a`` in scenario ``s``.

    The four instrument families differ only here, which is what lets the paper
    compare them on exactly the same model.
    """
    if family not in FAMILIES:
        raise KeyError(f"unknown instrument family {family!r}")
    d = inst.dist[a]
    e = inst.e_elec
    ps = inst.psave
    zero = CONST0

    def theta(scen):
        key_scen = scen if family == "F4" else "*"
        return tuple((("theta", key_scen, k), v) for k, v in enumerate(inst.theta_menu))

    def sigma(scen):
        key_scen = scen if family == "F4" else "*"
        return tuple((("sigma", key_scen, k), v) for k, v in enumerate(inst.sigma_menu))

    if family == "F0":
        return zero

    if family == "F1":                     # flat per-truck-km, no discount
        if kind in ("xE", "xD"):
            return LeaderTerm(0.0, tuple((b, c * d) for b, c in theta(s)))
        return zero

    if family == "F2":                     # full waiver for platooned trucks
        if kind in ("xE", "xD"):
            return LeaderTerm(0.0, tuple((b, c * d) for b, c in theta(s)))
        if kind in ("pE", "pD"):
            return LeaderTerm(0.0, tuple((b, -c * d) for b, c in theta(s)))
        return zero

    # F3 / F4: platoon-*discounted* charge on diesel truck-km, and a per-kWh
    # surcharge on charging (which is itself platoon-discounted because a
    # platooned electric truck draws less energy).
    if kind == "xD":
        return LeaderTerm(0.0, tuple((b, c * d) for b, c in theta(s)))
    if kind == "pD":
        return LeaderTerm(0.0, tuple((b, -c * d * ps) for b, c in theta(s)))
    if kind == "xE":
        return LeaderTerm(0.0, tuple((b, c * d * e) for b, c in sigma(s)))
    if kind == "pE":
        return LeaderTerm(0.0, tuple((b, -c * d * e * ps) for b, c in sigma(s)))
    return zero


def _menu_max(t: LeaderTerm) -> float:
    """Largest value ``t`` can take over any feasible leader decision.

    Menu-selection binaries form SOS1 groups (exactly one is 1), so the group
    contributes its largest coefficient; independent binaries (``y``, ``bay``)
    contribute their positive part.
    """
    groups: Dict[Hashable, List[float]] = {}
    free = 0.0
    for k, c in t.lin:
        if k[0] in ("theta", "sigma"):
            groups.setdefault((k[0], k[1]), []).append(c)
        else:
            free += max(c, 0.0)
    return t.const + free + sum(max(v) for v in groups.values())


def _menu_min(t: LeaderTerm) -> float:
    groups: Dict[Hashable, List[float]] = {}
    free = 0.0
    for k, c in t.lin:
        if k[0] in ("theta", "sigma"):
            groups.setdefault((k[0], k[1]), []).append(c)
        else:
            free += min(c, 0.0)
    return t.const + free + sum(min(v) for v in groups.values())


def instrument_keys(inst: Instance, family: str):
    """The (name, scenario-key) pairs of menu-selection binaries this family needs."""
    if family == "F0":
        return []
    if family in ("F1", "F2"):
        return [("theta", "*")]
    if family == "F3":
        return [("theta", "*"), ("sigma", "*")]
    return [("theta", s) for s in inst.S] + [("sigma", s) for s in inst.S]


# --------------------------------------------------------------------------- #
#  the lower-level LP itself                                                   #
# --------------------------------------------------------------------------- #
def build_follower(inst: Instance, s: str, family: str = "F4",
                   platoon_share_cap: float | None = None) -> FollowerLP:
    """Build the coalition's operating LP for scenario ``s``.

    Decision variables (all >= 0)
        fo[c,a]   loaded outbound container-truck flow of carrier c on arc a
        fi[c,a]   loaded inbound  container-truck flow of carrier c on arc a
        z[a]      empty container-truck flow, *pooled across the coalition*
        xE[a]     electric truck movements on arc a
        xD[a]     diesel   truck movements on arc a
        pE[a]     electric truck movements that travel in a platoon
        pD[a]     diesel   truck movements that travel in a platoon
        uI[c,n]   unmet import demand
        uE[c,n]   unmet export demand
    """
    lp = FollowerLP(scenario=s)
    if platoon_share_cap is None:
        platoon_share_cap = inst.rho
    C, A, Dn = inst.C, inst.arcs, inst.Dn
    o = inst.o
    cap = inst.Cap
    dist = inst.dist

    big_flow = max(cap.values())

    # ---- variables -------------------------------------------------------- #
    for c in C:
        for a in A:
            lp.add_var(("fo", c, a), f"fo[{c},{a}]", big_flow, CONST0)
            lp.add_var(("fi", c, a), f"fi[{c},{a}]", big_flow, CONST0)
    for a in A:
        lp.add_var(("z", a), f"z[{a}]", big_flow, CONST0)

    for a in A:
        d = dist[a]
        e_edge = inst.edge_of_arc[a]
        cE = const(inst.wage * d + inst.price[s] * inst.e_elec * d) \
            + charge_terms(inst, family, s, a, "xE")
        cD = const(inst.wage * d + inst.p_diesel * inst.f_diesel * d) \
            + charge_terms(inst, family, s, a, "xD")
        cpE = const(inst.c_plat - inst.psave * inst.price[s] * inst.e_elec * d) \
            + charge_terms(inst, family, s, a, "pE")
        cpD = const(inst.c_plat - inst.psave * inst.p_diesel * inst.f_diesel * d) \
            + charge_terms(inst, family, s, a, "pD")
        #  Electric operation on a non-electrified edge needs no constraint of
        #  its own and no big-M: the charging-capacity row (R7) together with
        #  the leader-side coupling bay <= y already forces it to zero.  See
        #  Lemma 2 in the manuscript for the two-line argument.
        lp.add_var(("xE", a), f"xE[{a}]", cap[a], cE)
        lp.add_var(("xD", a), f"xD[{a}]", cap[a], cD)
        lp.add_var(("pE", a), f"pE[{a}]", cap[a], cpE)
        lp.add_var(("pD", a), f"pD[{a}]", cap[a], cpD)

    #  Unmet demand is capped at the demand itself.  That cap is *not* implied
    #  by any other row, so it is written as a row rather than as a variable
    #  bound: a bound carries no dual, and the strong-duality certificate would
    #  then certify a different linear program from the one being solved.
    for c in C:
        for n in Dn:
            lp.add_var(("uI", c, n), f"uI[{c},{n}]", inst.DI[(c, n, s)], const(inst.PEN))
            lp.add_var(("uE", c, n), f"uE[{c},{n}]", inst.DE[(c, n, s)], const(inst.PEN))

    ix = lp.index
    out_a = {n: [a for a in A if a[0] == n] for n in inst.nodes}
    in_a = {n: [a for a in A if a[1] == n] for n in inst.nodes}

    # ---- (R1) outbound loaded flow reaches every demand node --------------- #
    for c in C:
        for n in inst.nodes:
            if n == o:
                continue
            coef: Dict[int, float] = {}
            for a in in_a[n]:
                coef[ix[("fo", c, a)]] = coef.get(ix[("fo", c, a)], 0.0) + 1.0
            for a in out_a[n]:
                coef[ix[("fo", c, a)]] = coef.get(ix[("fo", c, a)], 0.0) - 1.0
            rhs = 0.0
            if n in Dn:
                coef[ix[("uI", c, n)]] = 1.0
                rhs = inst.DI[(c, n, s)]
            lp.add_row(coef, const(rhs), f"import[{c},{n}]")

    # ---- (R2) inbound loaded flow leaves every demand node ----------------- #
    for c in C:
        for n in inst.nodes:
            if n == o:
                continue
            coef = {}
            for a in out_a[n]:
                coef[ix[("fi", c, a)]] = coef.get(ix[("fi", c, a)], 0.0) + 1.0
            for a in in_a[n]:
                coef[ix[("fi", c, a)]] = coef.get(ix[("fi", c, a)], 0.0) - 1.0
            rhs = 0.0
            if n in Dn:
                coef[ix[("uE", c, n)]] = 1.0
                rhs = inst.DE[(c, n, s)]
            lp.add_row(coef, const(rhs), f"export[{c},{n}]")

    # ---- (R3) empty-container balance, pooled over the coalition ----------- #
    #  net empties released at n  =  loaded arrivals - loaded departures
    #  and they must be moved out (surplus) or brought in (deficit): equality.
    for n in inst.nodes:
        if n == o:
            continue
        coef = {}
        for a in out_a[n]:
            coef[ix[("z", a)]] = coef.get(ix[("z", a)], 0.0) + 1.0
        for a in in_a[n]:
            coef[ix[("z", a)]] = coef.get(ix[("z", a)], 0.0) - 1.0
        rhs = 0.0
        if n in Dn:
            for c in C:
                coef[ix[("uI", c, n)]] = coef.get(ix[("uI", c, n)], 0.0) + 1.0
                coef[ix[("uE", c, n)]] = coef.get(ix[("uE", c, n)], 0.0) - 1.0
                rhs += inst.DI[(c, n, s)] - inst.DE[(c, n, s)]
        lp.add_eq(coef, const(rhs), f"empty[{n}]")

    # ---- (R4) every container movement needs a truck ----------------------- #
    for a in A:
        coef = {ix[("xE", a)]: 1.0, ix[("xD", a)]: 1.0, ix[("z", a)]: -1.0}
        for c in C:
            coef[ix[("fo", c, a)]] = -1.0
            coef[ix[("fi", c, a)]] = -1.0
        lp.add_row(coef, const(0.0), f"trucks[{a}]")

    # ---- (R6) platoon volumes are bounded by the fleet that can platoon ---- #
    for a in A:
        lp.add_row({ix[("xE", a)]: 1.0, ix[("pE", a)]: -1.0}, const(0.0), f"platE[{a}]")
        lp.add_row({ix[("xD", a)]: 1.0, ix[("pD", a)]: -1.0}, const(0.0), f"platD[{a}]")
        lp.add_row({ix[("xE", a)]: platoon_share_cap, ix[("xD", a)]: platoon_share_cap,
                    ix[("pE", a)]: -1.0, ix[("pD", a)]: -1.0}, const(0.0), f"platcap[{a}]")

    # ---- (R7) charging capacity installed on the edge ---------------------- #
    for e in inst.edges:
        coef = {}
        for a in inst.arcs_of_edge[e]:
            coef[ix[("xE", a)]] = -inst.e_elec * dist[a]
            coef[ix[("pE", a)]] = inst.e_elec * dist[a] * inst.psave
        if e in inst.E:
            #  -energy(e) >= -g(e), i.e. the energy drawn on the edge may not
            #  exceed the charging capacity the leader installs there.
            lin = tuple((("bay", e, b), -inst.resource_share * inst.module_kwh * (2 ** b))
                        for b in range(inst.n_bits))
            lp.add_row(coef, LeaderTerm(0.0, lin), f"chgcap[{e}]")
        else:
            lp.add_row(coef, const(0.0), f"chgcap[{e}]")

    # ---- (R8) system-wide charging headroom in this grid state ------------- #
    coef = {}
    for a in A:
        coef[ix[("xE", a)]] = -inst.e_elec * dist[a]
        coef[ix[("pE", a)]] = inst.e_elec * dist[a] * inst.psave
    lp.add_row(coef, const(-inst.Gavail[s]), "gridcap")

    # ---- (R9) physical arc capacity ---------------------------------------- #
    for a in A:
        lp.add_row({ix[("xE", a)]: -1.0, ix[("xD", a)]: -1.0}, const(-cap[a]), f"arccap[{a}]")

    # ---- (R10) unmet demand cannot exceed demand --------------------------- #
    for c in C:
        for n in Dn:
            lp.add_row({ix[("uI", c, n)]: -1.0}, const(-inst.DI[(c, n, s)]), f"ucapI[{c},{n}]")
            lp.add_row({ix[("uE", c, n)]: -1.0}, const(-inst.DE[(c, n, s)]), f"ucapE[{c},{n}]")

    return lp


# --------------------------------------------------------------------------- #
#  social (leader) accounting for one scenario, as a function of follower vars  #
# --------------------------------------------------------------------------- #
def social_coefficients(inst: Instance, s: str) -> Tuple[Dict[Hashable, float],
                                                         Dict[Hashable, float],
                                                         Dict[Hashable, float]]:
    """Return (operating cost, emissions, grid load) coefficient dictionaries.

    Keys are follower-variable keys; values are per-unit coefficients.  Corridor
    charges are *transfers* between the coalition and the authority and are
    therefore excluded from the social operating cost.
    """
    op: Dict[Hashable, float] = {}
    em: Dict[Hashable, float] = {}
    gr: Dict[Hashable, float] = {}
    for a in inst.arcs:
        d = inst.dist[a]
        op[("xE", a)] = inst.wage * d + inst.price[s] * inst.e_elec * d
        op[("xD", a)] = inst.wage * d + inst.p_diesel * inst.f_diesel * d
        op[("pE", a)] = inst.c_plat - inst.psave * inst.price[s] * inst.e_elec * d
        op[("pD", a)] = inst.c_plat - inst.psave * inst.p_diesel * inst.f_diesel * d
        em[("xE", a)] = inst.ef[s] * inst.e_elec * d
        em[("pE", a)] = -inst.psave * inst.ef[s] * inst.e_elec * d
        em[("xD", a)] = inst.ef_diesel * inst.f_diesel * d
        em[("pD", a)] = -inst.psave * inst.ef_diesel * inst.f_diesel * d
        gr[("xE", a)] = inst.e_elec * d
        gr[("pE", a)] = -inst.psave * inst.e_elec * d
    for c in inst.C:
        for n in inst.Dn:
            op[("uI", c, n)] = inst.PEN
            op[("uE", c, n)] = inst.PEN
    return op, em, gr


def pigouvian_levels(inst: Instance) -> Tuple[float, Dict[str, float]]:
    """The closed-form first-best instrument levels of Theorem 2.

    theta* = w_emis * ef_diesel * f_diesel        (USD per diesel truck-km)
    sigma*_s = w_emis * ef_s + w_grid             (USD per kWh charged)
    """
    theta = inst.w_emis * inst.ef_diesel * inst.f_diesel
    sigma = {s: inst.w_emis * inst.ef[s] + inst.w_grid for s in inst.S}
    return theta, sigma
