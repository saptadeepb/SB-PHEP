"""
models.py
=========
Exact optimisation models for SB-PHEP-II.  Everything is a linear or
mixed-integer linear program solved to certified optimality with HiGHS through
Pyomo; no heuristic or metaheuristic is used anywhere in the paper.

Models
------
``follower_lp``      the carrier coalition's operating LP for one scenario with
                     the leader's decisions fixed.  Used to price coalitions in
                     the cooperative game and to validate both reformulations.
``centralized``      the social planner's problem (first best).  A lower bound
                     on what any Stackelberg tariff can achieve.
``bilevel_sd``       the proposed single-level reformulation: primal
                     feasibility + dual feasibility + strong duality, with every
                     leader x follower product linearised exactly because all
                     leader instruments are discrete.  No complementarity
                     binaries at all.
``bilevel_kkt``      the classical KKT / big-M single-level reformulation, kept
                     as an independent cross-check on ``bilevel_sd`` and as the
                     baseline in the scalability study.
``enumerate_leader`` brute-force enumeration of the leader's design space, used
                     only on the smallest instances to certify both
                     reformulations against a method that cannot be wrong.
"""
from __future__ import annotations

import itertools
import time
from typing import Dict, Hashable, List, Optional, Tuple

import pyomo.environ as pyo

from . import lp as L
from .instance import Instance

TOL = 1e-6


# --------------------------------------------------------------------------- #
#  solver plumbing                                                             #
# --------------------------------------------------------------------------- #
def _solve(m, mip_gap: float = 0.0, tee: bool = False, time_limit: float = 900.0):
    """A fresh HiGHS solver object per call.

    The persistent ``appsi`` HiGHS wrapper must not be reused across freshly
    built ``ConstraintList`` models: it can silently drop constraints added
    after the first solve.  Constructing a new object each time is cheap
    relative to the solves and removes that failure mode entirely.
    """
    from pyomo.contrib.appsi.solvers.highs import Highs

    opt = Highs()
    opt.config.stream_solver = tee
    opt.config.mip_gap = mip_gap
    opt.config.time_limit = time_limit
    opt.config.load_solution = False
    res = opt.solve(m)
    tc = str(res.termination_condition).split(".")[-1]
    #  "ok" means a solution was loaded; "certified" means the solver proved
    #  optimality.  Anything that stops on a limit is usable as an incumbent but
    #  must never be reported as an optimum.
    ok = tc in ("optimal", "feasible", "maxTimeLimit", "maxIterations")
    if ok and res.best_feasible_objective is not None:
        res.solution_loader.load_vars()
        if want_duals(m):
            try:
                m.dual.update(res.solution_loader.get_duals())
            except Exception:
                pass
    else:
        ok = False
    return res, tc, ok


def _certified(tc: str) -> bool:
    return tc == "optimal"


def _gap(res) -> float:
    """Relative optimality gap actually certified by the solver."""
    try:
        inc = res.best_feasible_objective
        bnd = res.best_objective_bound
        if inc is None or bnd is None:
            return float("nan")
        return abs(inc - bnd) / max(1.0, abs(inc))
    except Exception:
        return float("nan")


def want_duals(m) -> bool:
    return hasattr(m, "dual")


class _Bilin:
    """Exact linearisation of (binary x bounded continuous) products.

    For a binary ``b`` and a continuous ``t`` with ``lo <= t <= up`` the product
    ``w = b*t`` is represented by the McCormick system

        w <= up*b,  w >= lo*b,  w <= t - lo*(1-b),  w >= t - up*(1-b),

    which is *exact* (not a relaxation) whenever ``b`` is binary and the bounds
    are valid.  Products are cached so that a given pair is linearised once.
    """

    def __init__(self, model, name="bl"):
        self.m = model
        self.name = name
        self.k = 0
        self.vars = pyo.VarList(domain=pyo.Reals)
        self.cons = pyo.ConstraintList()
        setattr(model, name + "_v", self.vars)
        setattr(model, name + "_c", self.cons)

    def prod(self, b, expr, lo: float, up: float):
        if up < lo:
            lo, up = up, lo
        w = self.vars.add()
        w.setlb(min(0.0, lo))
        w.setub(max(0.0, up))
        self.cons.add(w <= up * b)
        self.cons.add(w >= lo * b)
        self.cons.add(w <= expr - lo * (1 - b))
        self.cons.add(w >= expr - up * (1 - b))
        self.k += 1
        return w


# --------------------------------------------------------------------------- #
#  leader variable block                                                       #
# --------------------------------------------------------------------------- #
def _leader_block(m, inst: Instance, family: str,
                  fix_y=None, fix_bays=None, fix_theta=None, fix_sigma=None):
    """Create the leader's discrete decision variables and their constraints."""
    m.y = pyo.Var(inst.E, domain=pyo.Binary)
    m.bay = pyo.Var(((e, b) for e in inst.E for b in range(inst.n_bits)),
                    domain=pyo.Binary)
    m.leadcon = pyo.ConstraintList()
    for e in inst.E:
        for b in range(inst.n_bits):
            m.leadcon.add(m.bay[e, b] <= m.y[e])       # no bays without a site

    keys = L.instrument_keys(inst, family)
    m.sel = pyo.Var(((nm, sk, k) for (nm, sk) in keys
                     for k in range(len(inst.theta_menu if nm == "theta" else inst.sigma_menu))),
                    domain=pyo.Binary)
    for (nm, sk) in keys:
        menu = inst.theta_menu if nm == "theta" else inst.sigma_menu
        m.leadcon.add(sum(m.sel[nm, sk, k] for k in range(len(menu))) == 1)

    if fix_y is not None:
        for e in inst.E:
            m.y[e].fix(int(round(fix_y[e])))
    if fix_bays is not None:
        for e in inst.E:
            nb = int(round(fix_bays[e]))
            for b in range(inst.n_bits):
                m.bay[e, b].fix((nb >> b) & 1)
    for nm, fixv in (("theta", fix_theta), ("sigma", fix_sigma)):
        if fixv is None:
            continue
        menu = inst.theta_menu if nm == "theta" else inst.sigma_menu
        for (kn, sk) in keys:
            if kn != nm:
                continue
            val = fixv[sk] if isinstance(fixv, dict) else fixv
            k = min(range(len(menu)), key=lambda i: abs(menu[i] - val))
            for i in range(len(menu)):
                m.sel[nm, sk, i].fix(1 if i == k else 0)
    return keys


def _leader_expr(m, inst: Instance, key: Hashable):
    """Map a ``LeaderTerm`` binary key onto its Pyomo variable."""
    tag = key[0]
    if tag == "y":
        return m.y[key[1]]
    if tag == "bay":
        return m.bay[key[1], key[2]]
    if tag in ("theta", "sigma"):
        return m.sel[key[0], key[1], key[2]]
    raise KeyError(f"unknown leader key {key!r}")


def _leader_key_scenario(inst: Instance, family: str, nm: str, s: str) -> str:
    return s if family == "F4" else "*"


def _term_expr(m, inst: Instance, t: L.LeaderTerm):
    e = t.const
    for k, c in t.lin:
        e = e + c * _leader_expr(m, inst, k)
    return e


def _investment(m, inst: Instance):
    inv = 0
    for e in inst.E:
        km = inst.dist[inst.arcs_of_edge[e][0]]
        inv += (inst.K_fix[e] + inst.K_km[e] * km) * m.y[e]
        for b in range(inst.n_bits):
            inv += inst.module_cost * (2 ** b) * m.bay[e, b]
    return inv


# --------------------------------------------------------------------------- #
#  1. lower-level LP with the leader fixed                                     #
# --------------------------------------------------------------------------- #
def follower_lp(inst: Instance, s: str, leader: dict, family: str = "F4",
                want_duals: bool = False, tee: bool = False):
    """Solve the coalition's LP for scenario ``s``.

    ``leader`` is a plain dict with keys ``y`` (edge -> 0/1), ``bays``
    (edge -> integer bays), ``theta`` (scalar or scenario dict) and ``sigma``.
    """
    flp = L.build_follower(inst, s, family)
    m = pyo.ConcreteModel()
    m.J = pyo.RangeSet(0, flp.n_vars - 1)
    m.x = pyo.Var(m.J, domain=pyo.NonNegativeReals)
    for j in range(flp.n_vars):
        m.x[j].setub(flp.var_ub[j])

    val = _leader_values(inst, family, leader)

    def cval(t: L.LeaderTerm) -> float:
        return t.const + sum(c * val[k] for k, c in t.lin)

    m.OBJ = pyo.Objective(expr=sum(cval(flp.cost[j]) * m.x[j] for j in range(flp.n_vars)),
                          sense=pyo.minimize)
    m.R = pyo.ConstraintList()
    if want_duals:
        m.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    rows = []
    for r in flp.rows:
        rows.append(m.R.add(sum(c * m.x[j] for j, c in r.coef.items()) >= cval(r.rhs)))

    res, tc, ok = _solve(m, tee=tee)
    if not ok or not _certified(tc):
        #  The lower level is a linear program; anything other than a certified
        #  optimum means the instance or the leader decision is malformed, and
        #  silently returning an incumbent would corrupt the cooperative game
        #  and the fidelity test.
        return None, {"status": tc}
    x = {k: pyo.value(m.x[j]) for k, j in flp.index.items()}
    out = {"status": tc, "x": x, "obj": pyo.value(m.OBJ), "lp": flp}
    if want_duals:
        out["duals"] = [abs(m.dual.get(rows[i], 0.0)) for i in range(len(rows))]
    return pyo.value(m.OBJ), out


def _leader_values(inst: Instance, family: str, leader: dict) -> Dict[Hashable, float]:
    """Expand a plain leader dict into the binary-key valuation used by LeaderTerm."""
    val: Dict[Hashable, float] = {}
    y = leader.get("y", {e: 0 for e in inst.E})
    bays = leader.get("bays", {e: 0 for e in inst.E})
    for e in inst.E:
        val[("y", e)] = float(y[e])
        nb = int(round(bays[e]))
        for b in range(inst.n_bits):
            val[("bay", e, b)] = float((nb >> b) & 1)
    for nm, menu in (("theta", inst.theta_menu), ("sigma", inst.sigma_menu)):
        raw = leader.get(nm, 0.0)
        for (kn, sk) in L.instrument_keys(inst, family):
            if kn != nm:
                continue
            v = raw[sk] if isinstance(raw, dict) else raw
            k = min(range(len(menu)), key=lambda i: abs(menu[i] - v))
            for i in range(len(menu)):
                val[(nm, sk, i)] = 1.0 if i == k else 0.0
    return val


# --------------------------------------------------------------------------- #
#  scenario-replicated follower block shared by every single-level model        #
# --------------------------------------------------------------------------- #
def _follower_block(m, inst: Instance, family: str):
    lps = {s: L.build_follower(inst, s, family) for s in inst.S}
    m.SIDX = pyo.Set(initialize=list(inst.S), ordered=True)
    pairs = [(s, j) for s in inst.S for j in range(lps[s].n_vars)]
    m.x = pyo.Var(pairs, domain=pyo.NonNegativeReals)
    for s in inst.S:
        for j in range(lps[s].n_vars):
            m.x[s, j].setub(lps[s].var_ub[j])
    return lps


def _social_objective(m, inst: Instance, lps):
    """Investment + H * expected weighted social cost."""
    exp_op = exp_em = exp_gr = 0
    for s in inst.S:
        op_c, em_c, gr_c = L.social_coefficients(inst, s)
        ix = lps[s].index
        op = sum(v * m.x[s, ix[k]] for k, v in op_c.items())
        em = sum(v * m.x[s, ix[k]] for k, v in em_c.items())
        gr = sum(v * m.x[s, ix[k]] for k, v in gr_c.items())
        exp_op += inst.prob[s] * op
        exp_em += inst.prob[s] * em
        exp_gr += inst.prob[s] * gr
    total = _investment(m, inst) + inst.H * (exp_op + inst.w_emis * exp_em + inst.w_grid * exp_gr)
    return total, inst.H * exp_op, inst.H * exp_em, inst.H * exp_gr


def _primal_feasibility(m, inst: Instance, lps, tag="PF"):
    con = pyo.ConstraintList()
    setattr(m, tag, con)
    handles = {}
    for s in inst.S:
        for i, r in enumerate(lps[s].rows):
            handles[(s, i)] = con.add(
                sum(c * m.x[s, j] for j, c in r.coef.items()) >= _term_expr(m, inst, r.rhs))
    return handles


# --------------------------------------------------------------------------- #
#  2. centralized social planner (first best)                                  #
# --------------------------------------------------------------------------- #
def centralized(inst: Instance, eps_emis: Optional[float] = None,
                eps_grid: Optional[float] = None, fix_y=None, fix_bays=None,
                tee: bool = False, time_limit: float = 900.0, mip_gap: float = 0.0):
    m = pyo.ConcreteModel()
    _leader_block(m, inst, "F0", fix_y=fix_y, fix_bays=fix_bays)
    lps = _follower_block(m, inst, "F0")
    _primal_feasibility(m, inst, lps)
    total, op, em, gr = _social_objective(m, inst, lps)
    m.OBJ = pyo.Objective(expr=total, sense=pyo.minimize)
    if eps_emis is not None:
        m.eps_e = pyo.Constraint(expr=em <= eps_emis)
    if eps_grid is not None:
        m.eps_g = pyo.Constraint(expr=gr <= eps_grid)
    t0 = time.time()
    res, tc, ok = _solve(m, tee=tee, time_limit=time_limit, mip_gap=mip_gap)
    if not ok:
        return {"status": tc, "runtime": time.time() - t0, "model": "centralized"}
    out = _extract(m, inst, lps, total, op, em, gr, "F0")
    out.update({"status": tc, "runtime": time.time() - t0, "model": "centralized",
                "mip_gap": _gap(res), "certified": _certified(tc)})
    return out


# --------------------------------------------------------------------------- #
#  3. proposed exact single-level reformulation (strong duality)               #
# --------------------------------------------------------------------------- #
def bilevel_sd(inst: Instance, family: str = "F4", dual_bounds=None,
               eps_emis: Optional[float] = None, eps_grid: Optional[float] = None,
               fix_y=None, fix_bays=None, fix_theta=None, fix_sigma=None,
               valid_inequalities: bool = True, tee: bool = False,
               time_limit: float = 900.0, mip_gap: float = 0.0):
    """Single-level MILP: primal feasibility, dual feasibility, strong duality.

    The reformulation is exact because (i) the follower problem is a linear
    program for every leader decision, so primal feasibility + dual feasibility
    + zero duality gap characterise optimality exactly, and (ii) every product
    of a leader decision with a follower variable or dual is a product of a
    *binary* with a bounded continuous variable and is linearised exactly.
    """
    from .bounds import dual_bounds_for

    m = pyo.ConcreteModel()
    _leader_block(m, inst, family, fix_y=fix_y, fix_bays=fix_bays,
                  fix_theta=fix_theta, fix_sigma=fix_sigma)
    lps = _follower_block(m, inst, family)
    _primal_feasibility(m, inst, lps)

    if dual_bounds is None:
        dual_bounds = dual_bounds_for(inst, family)

    bl = _dual_block_sd(m, inst, lps, dual_bounds)

    if valid_inequalities:
        _add_valid_inequalities(m, inst, lps, family)

    total, op, em, gr = _social_objective(m, inst, lps)
    m.OBJ = pyo.Objective(expr=total, sense=pyo.minimize)
    if eps_emis is not None:
        m.eps_e = pyo.Constraint(expr=em <= eps_emis)
    if eps_grid is not None:
        m.eps_g = pyo.Constraint(expr=gr <= eps_grid)

    t0 = time.time()
    res, tc, ok = _solve(m, tee=tee, time_limit=time_limit, mip_gap=mip_gap)
    rt = time.time() - t0
    if not ok:
        return {"status": tc, "runtime": rt, "model": f"sd-{family}",
                "n_bin": _count_binaries(m), "n_var": _count_vars(m),
                "n_con": _count_cons(m)}
    out = _extract(m, inst, lps, total, op, em, gr, family)
    out.update({"status": tc, "runtime": rt, "model": f"sd-{family}",
                "n_bin": _count_binaries(m), "n_var": _count_vars(m),
                "n_con": _count_cons(m), "n_bilinear": bl.k, "mip_gap": _gap(res),
                "certified": _certified(tc)})
    return out


# --------------------------------------------------------------------------- #
#  4. classical KKT / big-M reformulation (baseline and cross-check)           #
# --------------------------------------------------------------------------- #
def bilevel_kkt(inst: Instance, family: str = "F4", dual_bounds=None,
                slack_bounds=None, eps_emis=None, eps_grid=None,
                fix_y=None, fix_bays=None, fix_theta=None, fix_sigma=None,
                valid_inequalities: bool = True,
                tee: bool = False, time_limit: float = 900.0, mip_gap: float = 0.0):
    """Primal feasibility + dual feasibility + big-M complementary slackness.

    One binary per complementarity pair, i.e. ``|S| (rows + columns)`` binaries,
    against ``|E|(1+n_bits) + |menus|`` in :func:`bilevel_sd`.  Kept because two
    independent exact reformulations that agree to solver tolerance are much
    stronger evidence of correctness than one.
    """
    from .bounds import dual_bounds_for, slack_bounds_for

    m = pyo.ConcreteModel()
    _leader_block(m, inst, family, fix_y=fix_y, fix_bays=fix_bays,
                  fix_theta=fix_theta, fix_sigma=fix_sigma)
    lps = _follower_block(m, inst, family)
    _primal_feasibility(m, inst, lps)

    if dual_bounds is None:
        dual_bounds = dual_bounds_for(inst, family)
    if slack_bounds is None:
        slack_bounds = slack_bounds_for(inst, family)

    dpairs = [(s, i) for s in inst.S for i in range(lps[s].n_rows)]
    m.lam = pyo.Var(dpairs, domain=pyo.NonNegativeReals)
    for s in inst.S:
        for i in range(lps[s].n_rows):
            m.lam[s, i].setub(dual_bounds[s][i])

    m.DF = pyo.ConstraintList()
    m.CS = pyo.ConstraintList()
    m.br = pyo.Var(dpairs, domain=pyo.Binary)
    cpairs = [(s, j) for s in inst.S for j in range(lps[s].n_vars)]
    m.bc = pyo.Var(cpairs, domain=pyo.Binary)

    for s in inst.S:
        flp = lps[s]
        cols: Dict[int, List[Tuple[int, float]]] = {j: [] for j in range(flp.n_vars)}
        for i, r in enumerate(flp.rows):
            for j, c in r.coef.items():
                cols[j].append((i, c))
        # rows: lam_i * (A_i x - b_i) = 0
        for i, r in enumerate(flp.rows):
            slack = sum(c * m.x[s, j] for j, c in r.coef.items()) - _term_expr(m, inst, r.rhs)
            m.CS.add(m.lam[s, i] <= dual_bounds[s][i] * m.br[s, i])
            m.CS.add(slack <= slack_bounds[s][i] * (1 - m.br[s, i]))
        # columns: x_j * (c_j - A^T lam)_j = 0
        for j in range(flp.n_vars):
            red = _term_expr(m, inst, flp.cost[j]) - sum(c * m.lam[s, i] for i, c in cols[j])
            m.DF.add(red >= 0)
            m.CS.add(m.x[s, j] <= flp.var_ub[j] * m.bc[s, j])
            m.CS.add(red <= _redcost_bound(inst, flp, j, dual_bounds[s]) * (1 - m.bc[s, j]))

    if valid_inequalities:
        _add_valid_inequalities(m, inst, lps, family)

    total, op, em, gr = _social_objective(m, inst, lps)
    m.OBJ = pyo.Objective(expr=total, sense=pyo.minimize)
    if eps_emis is not None:
        m.eps_e = pyo.Constraint(expr=em <= eps_emis)
    if eps_grid is not None:
        m.eps_g = pyo.Constraint(expr=gr <= eps_grid)

    t0 = time.time()
    res, tc, ok = _solve(m, tee=tee, time_limit=time_limit, mip_gap=mip_gap)
    rt = time.time() - t0
    if not ok:
        return {"status": tc, "runtime": rt, "model": f"kkt-{family}",
                "n_bin": _count_binaries(m), "n_var": _count_vars(m),
                "n_con": _count_cons(m)}
    out = _extract(m, inst, lps, total, op, em, gr, family)
    out.update({"status": tc, "runtime": rt, "model": f"kkt-{family}",
                "n_bin": _count_binaries(m), "n_var": _count_vars(m),
                "n_con": _count_cons(m), "mip_gap": _gap(res),
                "certified": _certified(tc)})
    return out


def _redcost_bound(inst: Instance, flp: L.FollowerLP, j: int, dbound) -> float:
    """Valid upper bound on the reduced cost of column ``j``."""
    t = flp.cost[j]
    cmax = t.const + sum(max(c, 0.0) for _, c in t.lin)
    neg = 0.0
    for i, r in enumerate(flp.rows):
        c = r.coef.get(j, 0.0)
        if c < 0:
            neg += -c * dbound[i]
    return max(1.0, cmax + neg)


# --------------------------------------------------------------------------- #
#  valid inequalities                                                          #
# --------------------------------------------------------------------------- #
def _add_valid_inequalities(m, inst: Instance, lps, family: str):
    """Problem-specific cuts that are valid for every feasible leader decision.

    (VI1)  bays only on electrified edges (already in the leader block) and no
           electrification without at least one bay: an edge with a site but no
           charger can carry no electric truck, so it is dominated.
    (VI2)  charging headroom, *per edge*: no edge can usefully carry more
           capacity than the largest scenario headroom, plus the one procurement
           unit that lumpiness may force.
    The threshold preprocessing of Corollary 2 is *not* applied here, and the
    reason is worth recording. Its argument converts electric movements to diesel
    inside a given solution, which is valid when whoever chooses the operations
    is minimising social cost -- that is, in the centralized benchmark. Under a
    restricted instrument family the followers minimise their own cost, so
    removing a charging site makes them re-optimise, and their new private
    optimum need not be socially better than the converted point. The rule also
    needs the emission-neutral threshold, not only the social one, once an
    emission target is imposed. :func:`dominated_edges` is therefore reported as
    a diagnostic rather than used as a cut; on every instance in this study it is
    empty, so nothing would be fixed by it in any case.
    """
    m.VI = pyo.ConstraintList()
    for e in inst.E:
        m.VI.add(sum(m.bay[e, b] for b in range(inst.n_bits)) >= m.y[e])   # (VI1)

    #  (VI2) The obvious *aggregate* form -- total installed capacity at most the
    #  largest headroom -- is NOT valid: capacity is lumpy, so k edges each
    #  drawing a trickle of energy each need a whole unit, and the aggregate can
    #  exceed the headroom at the true optimum.  The per-edge form below is valid
    #  for the same reason the aggregate one is not: an edge drawing at most the
    #  system headroom needs at most one unit more than that headroom covers.
    gmax = max(inst.Gavail.values())                                        # (VI2)
    unit = inst.resource_share * inst.module_kwh
    for e in inst.E:
        m.VI.add(sum(unit * (2 ** b) * m.bay[e, b]
                     for b in range(inst.n_bits)) <= gmax + unit)


def dominated_edges(inst: Instance) -> List:
    """Edges a *social planner* would never electrify (Corollary 2).

    Electric traction on an arc is socially preferred to diesel only if

        e_elec (price_s + w_emis ef_s + w_grid)  <  f_diesel (p_diesel + w_emis ef_diesel)

    holds in at least one scenario.  If it fails in every scenario, the electric
    option is dominated arc-by-arc and, since the capital cost of a site is
    strictly positive, no optimal *centralized* solution electrifies the edge.

    This is a diagnostic, not a cut.  The conversion argument behind it holds for
    whoever is minimising social cost; under a restricted instrument family the
    followers minimise private cost and would re-optimise, so the rule is not
    applied to the bilevel models (see :func:`_add_valid_inequalities`).  It is
    empty on every instance in this study.
    """
    rhs = inst.f_diesel * (inst.p_diesel + inst.w_emis * inst.ef_diesel)
    out = []
    for e in inst.E:
        useful = any(inst.e_elec * (inst.price[s] + inst.w_emis * inst.ef[s] + inst.w_grid)
                     < rhs - 1e-12 for s in inst.S)
        if not useful:
            out.append(e)
    return out


def break_even_ef(inst: Instance, s: str) -> float:
    """Break-even grid carbon intensity of Proposition 5, in kgCO2/kWh.

    Electrification lowers weighted social cost in scenario ``s`` iff the grid
    emission factor is below this value.
    """
    num = inst.f_diesel * (inst.p_diesel + inst.w_emis * inst.ef_diesel) \
        - inst.e_elec * (inst.price[s] + inst.w_grid)
    return num / (inst.w_emis * inst.e_elec)


# --------------------------------------------------------------------------- #
#  5. brute-force enumeration (certification on tiny instances)                #
# --------------------------------------------------------------------------- #
def enumerate_leader(inst: Instance, family: str = "F4", max_designs: int = 4096,
                     time_limit: float = 900.0):
    """Enumerate every electrification pattern; optimise the rest exactly.

    For each ``y`` the remaining problem over bays and charge levels is still a
    bilevel program, so it is solved with :func:`bilevel_sd` with ``y`` fixed.
    This is the reference that cannot be wrong, and it is what "just enumerate the
    design space" amounts to as a solution method; the scalability
    study shows where it stops being possible.
    """
    n = len(inst.E)
    if 2 ** n > max_designs:
        raise ValueError(f"{2**n} designs exceeds max_designs={max_designs}")
    best, best_y, evaluated, uncertified = None, None, 0, 0
    t0 = time.time()
    for bits in itertools.product((0, 1), repeat=n):
        fy = {e: bits[i] for i, e in enumerate(inst.E)}
        r = bilevel_sd(inst, family, fix_y=fy, valid_inequalities=False,
                       time_limit=time_limit)
        evaluated += 1
        if not r.get("certified", False) and r.get("obj") is not None:
            uncertified += 1
        if r.get("obj") is not None and (best is None or r["obj"] < best["obj"] - 1e-9):
            best, best_y = r, fy
    return {"obj": None if best is None else best["obj"], "y": best_y,
            "designs": evaluated, "runtime": time.time() - t0,
            "model": f"enum-{family}", "best": best,
            "uncertified_subproblems": uncertified,
            "certified": uncertified == 0 and best is not None}


# --------------------------------------------------------------------------- #
#  extraction                                                                  #
# --------------------------------------------------------------------------- #
def _extract(m, inst: Instance, lps, total, op, em, gr, family: str) -> dict:
    y = {e: int(round(pyo.value(m.y[e]))) for e in inst.E}
    bays = {e: int(round(sum((2 ** b) * pyo.value(m.bay[e, b]) for b in range(inst.n_bits))))
            for e in inst.E}
    theta, sigma = {}, {}
    for (nm, sk) in L.instrument_keys(inst, family):
        menu = inst.theta_menu if nm == "theta" else inst.sigma_menu
        lvl = sum(menu[k] * pyo.value(m.sel[nm, sk, k]) for k in range(len(menu)))
        (theta if nm == "theta" else sigma)[sk] = round(lvl, 8)

    leader_dict = {"y": y, "bays": bays,
                   "theta": (theta.get("*") if "*" in theta else theta) if theta else 0.0,
                   "sigma": (sigma.get("*") if "*" in sigma else sigma) if sigma else 0.0}
    val = _leader_values(inst, family, leader_dict)

    perS, follower_obj = {}, {}
    for s in inst.S:
        ix = lps[s].index
        op_c, em_c, gr_c = L.social_coefficients(inst, s)
        xs = {k: pyo.value(m.x[s, j]) for k, j in ix.items()}
        flp = lps[s]
        follower_obj[s] = sum(
            (flp.cost[j].const + sum(c * val[k] for k, c in flp.cost[j].lin))
            * pyo.value(m.x[s, j]) for j in range(flp.n_vars))
        perS[s] = {
            "op": sum(v * xs[k] for k, v in op_c.items()),
            "emis": sum(v * xs[k] for k, v in em_c.items()),
            "grid": sum(v * xs[k] for k, v in gr_c.items()),
            "trucks": sum(xs[("xE", a)] + xs[("xD", a)] for a in inst.arcs),
            "electric": sum(xs[("xE", a)] for a in inst.arcs),
            "platooned": sum(xs[("pE", a)] + xs[("pD", a)] for a in inst.arcs),
            "empty_km": sum(xs[("z", a)] * inst.dist[a] for a in inst.arcs),
            "unmet": sum(xs[("uI", c, n)] + xs[("uE", c, n)]
                         for c in inst.C for n in inst.Dn),
        }
    return {
        "obj": pyo.value(total), "invest": pyo.value(_investment(m, inst)),
        "exp_op": pyo.value(op), "exp_emis": pyo.value(em), "exp_grid": pyo.value(gr),
        "y": y, "bays": bays, "theta": theta, "sigma": sigma,
        "n_electrified": sum(y.values()), "perS": perS, "family": family,
        "follower_obj": follower_obj, "leader": leader_dict,
    }


def _count_binaries(m) -> int:
    return sum(1 for v in m.component_data_objects(pyo.Var, active=True)
               if v.is_binary() and not v.fixed)


def _count_vars(m) -> int:
    return sum(1 for _ in m.component_data_objects(pyo.Var, active=True))


def _count_cons(m) -> int:
    return sum(1 for _ in m.component_data_objects(pyo.Constraint, active=True))


def _dual_block_sd(m, inst: Instance, lps, dual_bounds):
    """Dual variables, dual feasibility and the strong-duality equality.

    Shared by :func:`bilevel_sd` and by the minimum-emissions model used to
    measure an instrument family's reach, so that both impose exactly the same
    notion of follower optimality.
    """
    dpairs = [(s, i) for s in inst.S for i in range(lps[s].n_rows)]
    m.lam = pyo.Var(dpairs, domain=pyo.NonNegativeReals)
    #  Only the duals that multiply a leader binary in the strong-duality
    #  equation need an upper bound, and those are exactly the rows whose
    #  right-hand side depends on the leader -- the charging-capacity rows,
    #  whose bound is proved in Proposition 1.  Every other dual is left free,
    #  so no unproved constant enters the proposed formulation anywhere.
    for s in inst.S:
        for i, r in enumerate(lps[s].rows):
            if r.rhs.lin:
                m.lam[s, i].setub(dual_bounds[s][i])

    # column-wise transpose
    m.DF = pyo.ConstraintList()
    for s in inst.S:
        flp = lps[s]
        cols: Dict[int, List[Tuple[int, float]]] = {j: [] for j in range(flp.n_vars)}
        for i, r in enumerate(flp.rows):
            for j, c in r.coef.items():
                cols[j].append((i, c))
        for j in range(flp.n_vars):
            m.DF.add(sum(c * m.lam[s, i] for i, c in cols[j])
                     <= _term_expr(m, inst, flp.cost[j]))

    # ---- strong duality --------------------------------------------------- #
    #  The products are grouped by leader binary before they are linearised.
    #  Writing  c(w)^T x = c0^T x + sum_k b_k (g_k^T x)  and
    #  b(w)^T lam = b0^T lam + sum_k b_k (h_k^T lam),  each leader binary needs a
    #  single McCormick block against one aggregate linear expression instead of
    #  one block per follower variable.  This is exact for the same reason the
    #  per-variable version is -- the multiplier is binary and the aggregate is
    #  bounded -- and it reduces the number of auxiliary variables from
    #  O(|S| |A| |menu|) to O(|S| (|menu| + |E| log m)).
    bl = _Bilin(m, "sd")
    m.SD = pyo.ConstraintList()
    for s in inst.S:
        flp = lps[s]
        lhs = sum(flp.cost[j].const * m.x[s, j] for j in range(flp.n_vars))
        groups: Dict[Hashable, List[Tuple[int, float]]] = {}
        for j in range(flp.n_vars):
            for k, c in flp.cost[j].lin:
                groups.setdefault(k, []).append((j, c))
        for k, terms in groups.items():
            expr = sum(c * m.x[s, j] for j, c in terms)
            lo = sum(min(c, 0.0) * flp.var_ub[j] for j, c in terms)
            hi = sum(max(c, 0.0) * flp.var_ub[j] for j, c in terms)
            lhs += bl.prod(_leader_expr(m, inst, k), expr, lo, hi)

        rhs = sum(r.rhs.const * m.lam[s, i] for i, r in enumerate(flp.rows))
        rgroups: Dict[Hashable, List[Tuple[int, float]]] = {}
        for i, r in enumerate(flp.rows):
            for k, c in r.rhs.lin:
                rgroups.setdefault(k, []).append((i, c))
        for k, terms in rgroups.items():
            expr = sum(c * m.lam[s, i] for i, c in terms)
            lo = sum(min(c, 0.0) * dual_bounds[s][i] for i, c in terms)
            hi = sum(max(c, 0.0) * dual_bounds[s][i] for i, c in terms)
            rhs += bl.prod(_leader_expr(m, inst, k), expr, lo, hi)

        m.SD.add(lhs <= rhs)      # weak duality gives >=, so <= closes the gap

    return bl
